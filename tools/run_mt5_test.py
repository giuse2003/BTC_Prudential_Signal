"""
Script di automazione per eseguire il backtest di BTC_Swing_Sentinel su MetaTrader 5 Strategy Tester.
Supporta TradingSphere MT5 e FTMO MT5.
Salva report e grafici sia in locale che su MEGA CLOUD, aggiornando i manifesti.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import shutil
import subprocess
import sys
import time
from bs4 import BeautifulSoup

ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent
SRC_EX5 = ROOT_DIR / "mt5/src/BTC_Swing_Sentinel_v100.ex5"
SRC_SET = ROOT_DIR / "mt5/presets/BTC_Swing_Sentinel_v100.set"

MEGA_OUT = pathlib.Path(r"D:\MEGA CLOUD\Trading\BTC SIGNAL\tests\MT5")
MEGA_OUT.mkdir(parents=True, exist_ok=True)

TERMINALS = {
    "tradingsphere": {
        "name": "TradingSphere MT5",
        "exe": pathlib.Path(r"C:\Program Files\TradingSphere MT5\terminal64.exe"),
        "data": pathlib.Path(r"C:\Users\giuse\AppData\Roaming\MetaQuotes\Terminal\AADFF1F701D2234AAC1234DE511D9D5D"),
        "login": "50004543",
        "server": "TradingSphere-Demo1",
        "symbol": "BTCUSD",
    },
    "ftmo": {
        "name": "FTMO MT5",
        "exe": pathlib.Path(r"C:\Program Files\FTMO Global Markets MT5 Terminal\terminal64.exe"),
        "data": pathlib.Path(r"C:\Users\giuse\AppData\Roaming\MetaQuotes\Terminal\81A933A9AFC5DE3C23B15CAB19C63850"),
        "login": "531451801",
        "server": "FTMO-Server3",
        "symbol": "BTCUSD",
    },
}


def run_tester(
    terminal_key: str = "tradingsphere",
    symbol: str = "BTCUSD",
    from_date: str = "2021.01.01",
    to_date: str = "2026.11.20",
    model: int = 1,  # 1 = Open prices only (fast for D1 bar strategy), 2 = 1-min OHLC, 4 = Real ticks
    deposit: int = 10000,
    timeout_sec: int = 300,
) -> dict:
    if terminal_key not in TERMINALS:
        raise ValueError(f"Terminale non valido: {terminal_key}. Scegli tra: {list(TERMINALS.keys())}")

    term = TERMINALS[terminal_key]
    term_exe = term["exe"]
    term_data = term["data"]
    login = term["login"]
    server = term["server"]

    if not term_exe.exists():
        raise FileNotFoundError(f"Eseguibile non trovato: {term_exe}")
    if not term_data.exists():
        raise FileNotFoundError(f"Cartella dati terminale non trovata: {term_data}")
    if not SRC_EX5.exists():
        raise FileNotFoundError(f"File compilato EX5 non trovato: {SRC_EX5}. Compilare prima l'EA!")

    test_name = f"BTC_Swing_Sentinel_{terminal_key}_{symbol}"
    print(f"\n=======================================================")
    print(f" Avvio MT5 Strategy Tester: {term['name']}")
    print(f" Simbolo: {symbol} | Periodo: D1 | Date: {from_date} -> {to_date}")
    print(f" Modello: {model} | Deposito: ${deposit}")
    print(f"=======================================================")

    # 1. Copia EX5 in MQL5/Experts
    experts_dir = term_data / "MQL5/Experts"
    experts_dir.mkdir(parents=True, exist_ok=True)
    dst_ex5 = experts_dir / SRC_EX5.name
    shutil.copy2(SRC_EX5, dst_ex5)
    print(f"[OK] EA copiato in: {dst_ex5}")

    # 2. Copia preset in MQL5/Profiles/Tester
    preset_dir = term_data / "MQL5/Profiles/Tester"
    preset_dir.mkdir(parents=True, exist_ok=True)
    dst_set = preset_dir / f"{test_name}.set"
    shutil.copy2(SRC_SET, dst_set)
    print(f"[OK] Preset copiato in: {dst_set}")

    # 3. Scrittura configurazione .ini
    cfg_dir = term_data / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    ini_path = cfg_dir / f"{test_name}.ini"

    ini_content = f"""[Common]
Login={login}
Server={server}

[Experts]
Enabled=1
AllowLiveTrading=0

[Tester]
Expert={SRC_EX5.name}
ExpertParameters={test_name}.set
Symbol={symbol}
Period=D1
Deposit={deposit}
Currency=USD
Leverage=1:1
Model={model}
ExecutionMode=0
Optimization=0
FromDate={from_date}
ToDate={to_date}
Report={test_name}.htm
ReplaceReport=1
ShutdownTerminal=1
Visual=0
"""
    ini_path.write_text(ini_content, encoding="utf-8")
    print(f"[OK] Configurazione INI generata: {ini_path}")

    # 4. Pulizia vecchi report
    target_report = term_data / f"{test_name}.htm"
    if target_report.exists():
        target_report.unlink()
    for png in term_data.glob(f"{test_name}*.png"):
        try:
            png.unlink()
        except Exception:
            pass

    # Chiudi istanze pendenti
    subprocess.run("taskkill /F /IM terminal64.exe /IM metatester64.exe /T", shell=True, capture_output=True)
    time.sleep(1)

    # 5. Avvio del Tester MT5
    cmd = f'"{term_exe}" /config:"{ini_path}"'
    print(f"[RUN] Esecuzione: {cmd}")
    start_time = time.time()
    subprocess.Popen(cmd, shell=True)

    completed = False
    while time.time() - start_time < timeout_sec:
        if target_report.exists() and target_report.stat().st_size > 1000:
            time.sleep(3)
            completed = True
            break
        time.sleep(2)

    elapsed = round(time.time() - start_time, 1)
    print(f"[STATUS] Tempo trascorso: {elapsed}s (Completato: {completed})")

    if not completed:
        print("[TIMEOUT/WARNING] Il terminale non ha ancora scritto il report HTML.")
        return {"completed": False, "elapsed": elapsed}

    # 6. Salvataggio e parsing del report
    dest_htm = MEGA_OUT / f"{test_name}.htm"
    shutil.copy2(target_report, dest_htm)

    png_files = []
    for png in term_data.glob(f"{test_name}*.png"):
        dest_png = MEGA_OUT / png.name
        shutil.copy2(png, dest_png)
        png_files.append(dest_png.name)

    print(f"[SAVED] Report salvato su MEGA: {dest_htm}")
    print(f"[SAVED] Grafici salvati: {png_files}")

    # Parsing metriche chiave
    raw_htm = dest_htm.read_bytes()
    html_txt = raw_htm.decode("utf-16" if raw_htm.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8", errors="replace")
    soup = BeautifulSoup(html_txt, "html.parser")

    results = {
        "completed": True,
        "elapsed": elapsed,
        "report_path": str(dest_htm),
        "terminal": term["name"],
        "symbol": symbol,
        "period": "D1",
        "png_files": png_files,
    }

    # Estrai tabella parametri
    for tr in soup.find_all("tr"):
        tds = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
        if len(tds) >= 2:
            key, val = tds[0], tds[1]
            if "Profitto Totale Netto" in key or "Total Net Profit" in key:
                results["net_profit"] = val
            elif "Fattore di Profitto" in key or "Profit Factor" in key:
                results["profit_factor"] = val
            elif "Drawdown Massima" in key or "Max Drawdown" in key or "Drawdown" in key:
                if "drawdown" not in results:
                    results["drawdown"] = val
            elif "Totale Operazioni" in key or "Total Trades" in key:
                results["total_trades"] = val
            elif "Indice di Sharpe" in key or "Sharpe" in key:
                results["sharpe"] = val

    print("\n--- Risultati Estratti ---")
    for k, v in results.items():
        if k not in ["report_path", "png_files"]:
            print(f"  {k}: {v}")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Esegui MT5 Strategy Tester per BTC Swing Sentinel")
    parser.add_argument("--terminal", default="tradingsphere", choices=["tradingsphere", "ftmo"])
    parser.add_argument("--symbol", default="BTCUSD")
    parser.add_argument("--from-date", default="2021.01.01")
    parser.add_argument("--to-date", default="2026.11.20")
    parser.add_argument("--model", type=int, default=1)
    parser.add_argument("--deposit", type=int, default=10000)
    args = parser.parse_args()

    res = run_tester(
        terminal_key=args.terminal,
        symbol=args.symbol,
        from_date=args.from_date,
        to_date=args.to_date,
        model=args.model,
        deposit=args.deposit,
    )
    if not res.get("completed"):
        sys.exit(1)
