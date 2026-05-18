# CBT - Cloud Migration Optimizer (M.I.E.R.D.A. Suite)

## 📖 Overview

The **Cloud Migration Optimizer** (Migration Interface for Efficient Relocation and Deployment Analysis) is a comprehensive solution designed to orchestrate, simulate, and analyze the massive migration of components and microservices from *On-Premise* environments to the *Cloud*. 

The platform evaluates dependencies, calculates critical paths (bottlenecks), and applies advanced heuristics to propose staged migration plans that ensure compliance with Service Level Agreements (SLAs), minimizing the impact of cross-traffic (hybrid) on network latency.

---

## 🏗️ System Architecture

The project is dockerized and divided into three main layers:

1. **Frontend (Interactive Dashboard):** Built with Astro, React, Tailwind CSS, and Apache ECharts. It provides a fluid graphical interface to configure parameters, launch simulations, and visualize massive dependency graphs.
2. **Backend (Mathematical Engine & API):** Developed in Python with FastAPI and NetworkX. It contains the algorithmic engines (`Guangorithm`, `Robergorithm V2`, and `Robergorithm V3`) capable of processing tens of thousands of nodes in seconds thanks to its highly optimized cycle cleaning features (DAGs).
3. **Database:** PostgreSQL. It stores the temporal history path by path (*Streaming* mode) for low RAM consumption during indexing.

---

## ⚙️ Prerequisites

To deploy the application, the environment must have:
- **Docker** (v20.10 or higher)
- **Docker Compose** (v2.0 or higher)

---

## 🚀 Installation and Deployment Instructions

The deployment is fully automated. To set up the environment:

1. **Clone/Extract the project** on the target machine.
2. **Configure Environment Variables (Optional):** In the `backend/src/` and `frontend/src/` folders, there are `.env.example` files. If you need to change passwords or URLs, copy them as `.env`. By default, Docker Compose will inject the necessary variables.
3. **Start the services:** Open a terminal at the root of the project (where `docker-compose.yaml` is located) and run:

```bash
   docker compose up -d --build

```

4. **Check the status:**
```bash
docker compose ps

```


*Note: The first time it runs, PostgreSQL will initialize the schema using the `init.sql` file. This may take a few seconds.*

---

## 🌐 Default Ports and Access

Once the containers are up, the services will be available at the following local ports (`localhost` or the machine's IP):

| Service | Access URL | Description |
| --- | --- | --- |
| **Frontend UI** | `http://localhost:4321` | Main control panel and simulation visualizer. This is the interface the end-user will use. |
| **Backend API** | `http://localhost:8000` | Orchestrator endpoints. Not usually consumed directly by the user. |
| **API Documentation (Swagger)** | `http://localhost:8000/docs` | Interactive documentation of all available endpoints (schemas, Pydantic, input/output methods). |
| **Database** | `localhost:5432` | Direct access to PostgreSQL (Default credentials in `docker-compose.yaml`). |

---

## 🖥️ Quick Start Guide

### 1. Simulation Setup

Access the Frontend interface (`http://localhost:4321`). The system will prompt you to upload the base data of the architecture to be evaluated:

* **Nodes:** CSV with the components/methods, specifying which are already in the Cloud.
* **Edges:** CSV with the dependencies and the base latency between them.
* **Mathematical Parameters:** You can define minimum/maximum migration capacities per stage, maximum tolerated latency (`l_max`), cross-traffic penalty (`l_extra`), and select the simulation engine.

### 2. Execution

Upon launching the simulation, the Backend will calculate the optimal plan. Depending on the volume (e.g., 200,000 components), the calculation will take anywhere from a few milliseconds to a few seconds.

### 3. Visualization and Interpretation (Topology Viewer)

Once the simulation is finished (`Completed` status), you can access the interactive graph viewer to audit the algorithm's decisions stage by stage.

#### 🎨 Visual Graph Legend

The visualizer is designed to provide immediate *feedback* on network stress. As you navigate through the temporal stages, the elements are colored under the following rules:

**Nodes (Components):**

* ⚪ **Gray (`On-Premise`):** The component still resides on traditional physical servers.
* 🔵 **Light Blue (`Cloud Node`):** The component is already operating in the Cloud environment (either from the initial state or from previous stages).
* 🔵✨ **Dark Blue Border and Glow (`Just Migrated`):** The node has just made the jump to the Cloud **exactly in this temporal stage**.

**Edges (Network Dependencies):**

* 🌫️ **Gray Line (`Stable`):** Standard connection with no critical penalties.
* ➖ **Solid Black Line (`Critical Path`):** Marks the "main artery" or the worst latency subpath. It is the uninterrupted route that is strangling the SLA at that exact moment.
* 〰️ **Dashed Red Line (`Cross-Traffic l_extra`):** Represents cross-traffic. One node is in the Cloud and the other is On-Premise, adding the hybrid latency penalty.
* 🔥 **Black Line with Red Glow (`Both`):** The worst-case scenario. The edge belongs to the structural critical path **AND ALSO** suffers from a hybrid traffic penalty.

*Tip: Hover over any line or node to display a card with the mathematical breakdown of latencies and the Method -> Component mapping.*

---

## 📚 Developer Documentation

All technical documentation regarding the API contract, JSON/Multipart upload schemas, and server responses is auto-generated based on the OpenAPI standard.

Please head to `http://localhost:8000/docs` to:

* Consult the Pydantic models.
* Test independent REST calls to the engine.
* Review standardized HTTP responses and error codes.

---

*M.I.E.R.D.A. Suite - Designed to ensure clean, scalable, and auditable technological transitions.*
"""

with open("index-v2.md", "w", encoding="utf-8") as f:
f.write(content)

print("File generated successfully.")

```
Tu archivo Markdown file is ready
[file-tag: code-generated-file-0-1779106237354081104]

He reescrito y traducido completamente la documentación técnica manteniendo la estructura, el tono profesional y todo el detalle de la arquitectura. Se ha respetado la nomenclatura y la descripción de los colores en el visor de topología para que encaje a la perfección con el frontend final.

```