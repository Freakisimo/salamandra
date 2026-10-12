import subprocess
import time
import os
import sys
import signal
from dotenv import load_dotenv

load_dotenv()

def run_agent(script_path: str, name: str, port: int) -> subprocess.Popen:
    print(f"[*] Starting {name} on port {port}...")
    python_path = os.path.join(os.getcwd(), "venv", "bin", "python")
    if not os.path.exists(python_path):
        python_path = sys.executable

    env = dict(os.environ)
    env["PYTHONPATH"] = os.getcwd()
    return subprocess.Popen([python_path, script_path], env=env)

def main():
    from src.core.registry import registry
    from src.config.settings import settings

    # Orchestrator is launched last so workers are up first
    worker_agents = registry.list_agents()
    
    agent_tasks = []
    for mod in worker_agents:
        agent_tasks.append((mod.script_path, mod.name, mod.port))
        
    # Append Orchestrator
    agent_tasks.append(("src/agents/orchestrator.py", "SalamandraOrchestrator", settings.ORCHESTRATOR_PORT))

    processes = []

    def shutdown(signum=None, frame=None):
        print("\n[!] Stopping Salamandra agents gracefully...")
        for proc in processes:
            try:
                proc.terminate()
            except Exception:
                pass
        for proc in processes:
            try:
                proc.wait(timeout=3)
            except Exception:
                proc.kill()
        print("[x] All agents stopped.")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        print("==================================================")
        print("     SALAMANDRA: Sistema Multi-Agente A2A         ")
        print("    Verificación de Noticias, OSINT y Memoria     ")
        print("==================================================")
        
        for script, name, port in agent_tasks:
            proc = run_agent(script, name, port)
            processes.append(proc)
            time.sleep(1.5) # Allow socket to bind

        print("\n[!] All Salamandra agents are running!")
        print(f"[-] Master Orchestrator listening at: http://localhost:{settings.ORCHESTRATOR_PORT}")
        print(f"[-] Person Directory DB at: {settings.DB_PATH}")
        print(f"[-] Immutable Ledger at: {settings.LEDGER_PATH}")
        print("[*] Press Ctrl+C to stop all agents.\n")

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        shutdown()

if __name__ == "__main__":
    if not os.getenv("GOOGLE_CLOUD_PROJECT") and not os.getenv("GCP_PROJECT"):
        print("NOTE: GOOGLE_CLOUD_PROJECT is not set. Defaulting to Vertex AI with Application Default Credentials.")
    main()
