from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from kubernetes import client, config
import os
from pathlib import Path
import logging

app = FastAPI(title="Kubernetes Resource Viewer")

# Create static directory if it doesn't exist
static_dir = Path("static")
static_dir.mkdir(exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to load kubeconfig, fall back to in-cluster config
try:
    config.load_kube_config()
except Exception as e:
    logger.warning(f"Could not load kubeconfig, trying in-cluster config: {e}")
    try:
        config.load_incluster_config()
    except Exception as e:
        logger.error(f"Could not load in-cluster config: {e}")

v1 = client.CoreV1Api()
apps_v1 = client.AppsV1Api()
batch_v1 = client.BatchV1Api()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/nodes")
async def get_nodes():
    try:
        nodes = v1.list_node()
        pods = v1.list_pod_for_all_namespaces()
        # Count pods per node
        pod_count_by_node = {}
        for pod in pods.items:
            node_name = pod.spec.node_name
            if node_name:
                pod_count_by_node[node_name] = pod_count_by_node.get(node_name, 0) + 1
        logger.info(f"Fetched {len(nodes.items)} nodes from the cluster.")
        return [{
            'name': node.metadata.name,
            'status': next((condition.status for condition in node.status.conditions if condition.type == 'Ready'), 'Unknown'),
            'cpu': node.status.capacity.get('cpu', 'N/A'),
            'memory': node.status.capacity.get('memory', 'N/A'),
            'pods': pod_count_by_node.get(node.metadata.name, 0),
            'pods_capacity': node.status.capacity.get('pods', 'N/A'),
            'architecture': node.status.node_info.architecture,
            'os': getattr(node.status.node_info, 'operating_system', getattr(node.status.node_info, 'os_image', 'N/A')),
            'kernel': node.status.node_info.kernel_version,
            'container_runtime': node.status.node_info.container_runtime_version
        } for node in nodes.items]
    except Exception as e:
        logger.error(f"Error fetching nodes: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching nodes: {e}")

@app.get("/api/namespaces")
async def get_namespaces():
    namespaces = v1.list_namespace()
    return [{
        'name': ns.metadata.name,
        'status': ns.status.phase
    } for ns in namespaces.items]

@app.get("/api/resources/{namespace}")
async def get_resources(namespace: str):
    resources = {
        'pods': [],
        'deployments': [],
        'services': [],
        'configmaps': [],
        'secrets': [],
        'jobs': []
    }
    
    # Get Pods
    pods = v1.list_namespaced_pod(namespace)
    resources['pods'] = [{
        'name': pod.metadata.name,
        'status': pod.status.phase,
        'containers': [c.name for c in pod.spec.containers],
        'node': pod.spec.node_name if pod.spec.node_name else 'Not Assigned'
    } for pod in pods.items]
    
    # Get Deployments
    deployments = apps_v1.list_namespaced_deployment(namespace)
    resources['deployments'] = [{
        'name': dep.metadata.name,
        'replicas': dep.spec.replicas,
        'available': dep.status.available_replicas
    } for dep in deployments.items]
    
    # Get Services
    services = v1.list_namespaced_service(namespace)
    resources['services'] = [{
        'name': svc.metadata.name,
        'type': svc.spec.type,
        'ports': [f"{p.port}/{p.protocol}" for p in svc.spec.ports]
    } for svc in services.items]
    
    # Get ConfigMaps
    configmaps = v1.list_namespaced_config_map(namespace)
    resources['configmaps'] = [{
        'name': cm.metadata.name,
        'data_keys': list(cm.data.keys()) if cm.data else []
    } for cm in configmaps.items]
    
    # Get Secrets
    secrets = v1.list_namespaced_secret(namespace)
    resources['secrets'] = [{
        'name': secret.metadata.name,
        'type': secret.type
    } for secret in secrets.items]
    
    # Get Jobs
    jobs = batch_v1.list_namespaced_job(namespace)
    resources['jobs'] = [{
        'name': job.metadata.name,
        'completions': job.spec.completions,
        'succeeded': job.status.succeeded
    } for job in jobs.items]
    
    return resources

@app.get("/api/pricing")
async def get_pricing():
    try:
        nodes = v1.list_node()
        # Pricing model (example):
        # $0.03 per vCPU per hour, $0.004 per GiB RAM per hour
        USD_PER_CPU_HOUR = 0.03
        USD_PER_GIB_HOUR = 0.004
        USD_TO_INR = 83
        total_cpu = 0
        total_mem_gib = 0
        for node in nodes.items:
            cpu = node.status.capacity.get('cpu', '0')
            # Handle millicores (e.g., '1000m')
            if isinstance(cpu, str) and cpu.endswith('m'):
                cpu_val = float(cpu[:-1]) / 1000.0
            else:
                cpu_val = float(cpu)
            total_cpu += cpu_val
            mem = node.status.capacity.get('memory', '0')
            # Remove 'Ki', 'Mi', 'Gi', etc.
            if isinstance(mem, str) and mem.endswith('Ki'):
                mem_gib = float(mem[:-2]) / 1048576
            elif isinstance(mem, str) and mem.endswith('Mi'):
                mem_gib = float(mem[:-2]) / 1024
            elif isinstance(mem, str) and mem.endswith('Gi'):
                mem_gib = float(mem[:-2])
            else:
                mem_gib = float(mem) / (1024**3)
            total_mem_gib += mem_gib
        # Calculate hourly price
        price_usd_hour = total_cpu * USD_PER_CPU_HOUR + total_mem_gib * USD_PER_GIB_HOUR
        price_inr_hour = price_usd_hour * USD_TO_INR
        return {
            'total_cpu': round(total_cpu, 2),
            'total_mem_gib': round(total_mem_gib, 2),
            'price_usd_hour': round(price_usd_hour, 2),
            'price_usd_day': round(price_usd_hour * 24, 2),
            'price_usd_month': round(price_usd_hour * 24 * 30, 2),
            'price_inr_hour': round(price_inr_hour, 2),
            'price_inr_day': round(price_inr_hour * 24, 2),
            'price_inr_month': round(price_inr_hour * 24 * 30, 2)
        }
    except Exception as e:
        logger.error(f"Error calculating pricing: {e}")
        raise HTTPException(status_code=500, detail=f"Error calculating pricing: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000) 