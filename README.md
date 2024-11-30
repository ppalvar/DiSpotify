# DiSpotify

**DiSpotify** is a distributed clone of Spotify designed to demonstrate the power of containerization and network separation. The project is structured to run in two Docker containers: one for the backend (server) and one for the frontend (client). These containers are placed in separate networks and communicate through a router container.

## Installation

To get DiSpotify up and running, you have two options: using Docker Compose for a streamlined setup or manually running each component. Below are the instructions for both methods.

### Using Docker Compose

1. Ensure you have Docker and Docker Compose installed on your machine.
2. Clone the repository:
   ```bash
   git clone https://github.com/ppalvar/DiSpotify.git
   cd DiSpotify
   ```
3. Run the Docker Compose file:
   ```bash
   docker-compose up --build
   ```
   This command will build and start all the necessary containers: router, frontend, and backend.

### Manual Setup

If you prefer to run each component manually, follow these steps:

1. **Build the Docker Images:**

   - **Router:**
     ```bash
     docker build -t router -f docker/router.Dockerfile .
     ```

   - **Frontend:**
     ```bash
     docker build -t frontend -f docker/frontend.Dockerfile .
     ```

   - **Backend:**
     ```bash
     docker build -t backend -f docker/backend.Dockerfile .
     ```

2. **Create Networks:**

   - **Clients Network:**
     ```bash
     docker network create --driver bridge --subnet 10.0.10.0/24 clients
     ```

   - **Servers Network:**
     ```bash
     docker network create --driver bridge --subnet 10.0.11.0/24 servers
     ```

3. **Run the Containers:**

   - **Router:**
     ```bash
     docker run -d --name router --cap-add NET_ADMIN --network clients --ip 10.0.10.254 --network servers --ip 10.0.11.254 router sleep infinity
     ```

   - **Frontend:**
     ```bash
     docker run -d --name frontend --cap-add NET_ADMIN --network clients -p 8080:8080 -p 8000:8000 -v $(pwd)/frontend:/app/frontend -w /app/frontend frontend sh -c "./startup.sh"
     ```

   - **Backend:**
     ```bash
     docker run -d --name backend --cap-add NET_ADMIN --network servers -v $(pwd)/backend:/app/backend -v $(pwd)/audios:/app/audios -w /app/backend backend sh -c "/app/backend.sh && python manage.py runserver 0.0.0.0:8000"
     ```

## Further Work

DiSpotify is an evolving project with plans to have a distributed architecture. Here are some future directions and considerations:

- **Distributed Architecture:** The project aims to fully leverage distributed systems to improve scalability, reliability, and performance. This will allow different components to be deployed across various geographical locations, enhancing user experience and system resilience.

- **Advantages of Distribution:**
  - **Scalability:** Easily scale individual components based on demand.
  - **Fault Tolerance:** Isolate failures to specific components, minimizing system-wide impact.
  - **Resource Optimization:** Allocate resources more efficiently across different nodes.

- **Technical Challenges:**
  - **Network Latency:** Ensuring low-latency communication between distributed components.
  - **Data Consistency:** Maintaining data integrity across distributed databases.
  - **Security:** Implementing robust security measures to protect data and communication channels.
  