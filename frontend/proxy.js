const http = require('http');
const httpProxy = require('http-proxy');
const axios = require('axios');

const subnet = '10.0.1';
const port = 8000;
const timeout = 1000;

const proxy = httpProxy.createProxyServer({});

let subnetIndex = 2;

async function isBackendAlive(ip) {
  try {
    const response = await axios.get(`http://${ip}:${port}/health`, { timeout });
    return response.status === 200;
  }

  catch (error) {
    return false;
  }
}

async function findAliveBackend() {
  for (let i = 0; i < 254; i++) {
    const currentIndex = (subnetIndex - 2 + i) % 11 + 2;
    const ip = `${subnet}.${currentIndex}`;

    if (await isBackendAlive(ip)) {
      console.log(`Found alive backend at ${ip}`);
      subnetIndex = currentIndex;
      return ip;
    }
  }
  console.error('No alive backend found in the subnet');
}

const server = http.createServer(async (req, res) => {
  try {
    const aliveBackend = await findAliveBackend();

    proxy.web(req, res, { target: `http://${aliveBackend}:${port}` }, (err) => {
      if (err) {
        console.error('Error forwarding request:', err);
        res.writeHead(500, { 'Content-Type': 'text/plain' });
        res.end('Error forwarding request');
      }
    });
  } catch (error) {
    console.error('No alive backend found:', error);
    res.writeHead(503, { 'Content-Type': 'text/plain' });
    res.end('No alive backend found');
  }
});

server.listen(8000, () => {
  console.log('Proxy server listening on http://localhost:8000');
});