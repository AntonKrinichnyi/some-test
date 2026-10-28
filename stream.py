#!/usr/bin/env python3
"""
Мост ZeroTier IPv6 -> локальный IPv4 для Mission Planner.

ZeroTier выдаёт борту адрес вида fd..., а Mission Planner в слушающем режиме
UDP умеет только IPv4. Скрипт забирает поток с борта по IPv6 и отдаёт его на
127.0.0.1, где Mission Planner его увидит. Команды и запросы параметров идут
обратно тем же путём.

Впиши адрес борта ниже и запусти:   python3 stream.py
В Mission Planner: режим UDP (слушающий), порт = LOCAL_PORT.
"""

# ═══════════════ НАСТРОЙКИ ═══════════════

# IPv6-адрес борта в сети ZeroTier. Без квадратных скобок.
# Посмотреть можно в консоли ZeroTier или на самом борту: ip -6 addr show dev zt+
DRONE_IP = "fd80:56c2:e21c:0000:0199:9300:aabb:ccdd"   # <-- сюда адрес борта из ZeroTier

# Порт, на котором борт отдаёт MAVLink (UdpEndpoint в main.conf).
DRONE_PORT = 14550

# Локальный порт для Mission Planner. Его же вписываешь в MP.
LOCAL_PORT = 14551

# False -- борт ждёт подключения (Mode=Server в main.conf), мы идём к нему. Обычный случай.
# True  -- борт сам шлёт на нас (Mode=Normal), мы только слушаем.
WAIT_FOR_DRONE = False

# Печатать статистику раз в N секунд. 0 -- не печатать.
STATS_EVERY = 5

# ═════════════ КОНЕЦ НАСТРОЕК ════════════


import select
import socket
import sys
import time


def resolve_v6(host, port):
    """Получить IPv6-адрес. Литерал разбираем напрямую, имя -- через DNS."""
    try:
        return socket.getaddrinfo(host, port, socket.AF_INET6, socket.SOCK_DGRAM,
                                  0, socket.AI_NUMERICHOST)[0][4]
    except socket.gaierror:
        pass  # не литерал -- пробуем как имя
    try:
        return socket.getaddrinfo(host, port, socket.AF_INET6, socket.SOCK_DGRAM)[0][4]
    except socket.gaierror as e:
        sys.exit("DRONE_IP: %s -- не IPv6-адрес и не имя с AAAA-записью (%s)" % (host, e))


def hint_no_data():
    print("\nПакетов с борта нет. Что проверить:", file=sys.stderr)
    print("  1. ZeroTier поднят и борт в сети:   zerotier-cli listnetworks",
          file=sys.stderr)
    print("  2. Борт пингуется:                  ping -6 %s" % DRONE_IP, file=sys.stderr)
    print("  3. Роутер на борту слушает IPv6. В /etc/mavlink-router/main.conf должно",
          file=sys.stderr)
    print("     быть  Address=[::]  , а не 0.0.0.0 -- иначе порт доступен только по IPv4.",
          file=sys.stderr)
    print("  4. Порт совпадает:                  DRONE_PORT = %d" % DRONE_PORT,
          file=sys.stderr)
    print("  5. Брандмауэр не режет исходящий UDP на этот порт.\n", file=sys.stderr)


def main():
    dest = ("127.0.0.1", LOCAL_PORT)

    up = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
    peer = None

    if WAIT_FOR_DRONE:
        try:
            up.bind(("::", DRONE_PORT))
        except OSError as e:
            sys.exit("не удалось занять порт %d: %s" % (DRONE_PORT, e))
        print("жду поток от борта на [::]:%d" % DRONE_PORT, flush=True)
    else:
        peer = resolve_v6(DRONE_IP, DRONE_PORT)
        print("подключаюсь к борту [%s]:%d" % (DRONE_IP, DRONE_PORT), flush=True)

    down = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    down.bind(("127.0.0.1", 0))

    print("отдаю на 127.0.0.1:%d  -- это и указывай в Mission Planner (режим UDP)"
          % LOCAL_PORT, flush=True)

    to_v4 = to_v6 = 0
    started = time.time()
    last_stats = started
    last_poke = 0.0
    warned = False

    try:
        while True:
            # пока борт не отозвался, периодически будим его пустым пакетом:
            # в режиме Server он молчит, пока не узнает адрес клиента
            if peer is not None and to_v4 == 0 and time.time() - last_poke >= 1.0:
                try:
                    up.sendto(b"", peer)
                except OSError as e:
                    sys.exit("не могу отправить на [%s]:%d -- %s" % (DRONE_IP, DRONE_PORT, e))
                last_poke = time.time()

            ready, _, _ = select.select([up, down], [], [], 1.0)

            for sock in ready:
                try:
                    data, addr = sock.recvfrom(65535)
                except OSError:
                    continue
                if not data:
                    continue

                if sock is up:
                    if peer is None:
                        peer = addr
                        print("борт найден: %s" % (addr[0],), flush=True)
                    if to_v4 == 0:
                        print("поток пошёл", flush=True)
                    down.sendto(data, dest)
                    to_v4 += 1
                elif peer is not None:
                    up.sendto(data, peer)
                    to_v6 += 1

            now = time.time()

            if not warned and to_v4 == 0 and now - started >= 10:
                hint_no_data()
                warned = True

            if STATS_EVERY and now - last_stats >= STATS_EVERY:
                print("  борт->MP: %d   MP->борт: %d" % (to_v4, to_v6), flush=True)
                last_stats = now

    except KeyboardInterrupt:
        print("\nостановлено. борт->MP: %d, MP->борт: %d" % (to_v4, to_v6))
    finally:
        up.close()
        down.close()


if __name__ == "__main__":
    main()
