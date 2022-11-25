import asyncio
import argparse
import logging
import subprocess

# How much time (in seconds) will be waiting for server to respond for the first time
TIMEOUT_INITIAL_REQUEST = 5

logging.basicConfig(format='[%(asctime)s %(levelname)s] %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def pipe(reader, writer):
    try:
        while not reader.at_eof():
            writer.write(await reader.read(2048))
    finally:
        writer.close()


class LifecycleManagingProxyServer:

    def __init__(self, proxy_ip, proxy_port, target_ip, target_port, cooldown_period, hook_start_svc, hook_stop_svc):
        self._proxy_ip = proxy_ip
        self._proxy_port = proxy_port
        self._target_ip = target_ip
        self._target_port = target_port
        self._cooldown_period = cooldown_period
        self._hook_start_svc = hook_start_svc
        self._hook_stop_svc = hook_stop_svc

        self._connected_clients = set()
        self._cooldown_task = None

    def _fire_start_hook(self):
        try:
            logging.info("Running 'start' hook")
            subprocess.run(self._hook_start_svc, check=True)
        except Exception as ex:
            logger.error("Error occurred while firing 'start' hook: ", ex)

    def _fire_stop_hook(self):
        try:
            logging.info("Running 'stop' hook")
            subprocess.run(self._hook_stop_svc, check=True)
        except Exception as ex:
            logger.error("Error ocurred while firing 'stop' hook: ", ex)

    async def _cooldown_and_fire_stop_hook(self):
        await asyncio.sleep(self._cooldown_period * 60)
        self._fire_stop_hook()
        self._cooldown_task = None

    def _start_cooldown(self):
        if len(self._connected_clients) > 0:
            return

        logger.info("No clients connected. Starting cooldown period.")
        self._cooldown_task = asyncio.create_task(self._cooldown_and_fire_stop_hook())

    def _reset_cooldown(self):
        if not self._cooldown_task:
            return

        logger.info("Clients connected. Cancelling cooldown task.")        
        self._cooldown_task.cancel()
        self._cooldown_task = None

    async def _check_if_running(self):
        try:
            future = asyncio.open_connection(self._target_ip, self._target_port)
            _, writer = await asyncio.wait_for(future, timeout=TIMEOUT_INITIAL_REQUEST)
            writer.close()

            logger.info("Target is up")
        except Exception as ex:
            logger.info("Target is down")
            self._fire_start_hook()

    async def _handle_client_connected(self, client_reader, client_writer):
        client_addr = client_writer.get_extra_info("peername")
        logger.info("Client connected: {}".format(client_addr))
        self._connected_clients.add(client_addr)
        self._reset_cooldown()

        await self._check_if_running()

        try:
            remote_reader, remote_writer = await asyncio.open_connection(self._target_ip, self._target_port)

            pipe_to_remote = pipe(client_reader, remote_writer)
            pipe_to_client = pipe(remote_reader, client_writer)
            await asyncio.gather(pipe_to_remote, pipe_to_client)
        finally:
            logger.info("Client disconnected: {}".format(client_addr))
            self._connected_clients.remove(client_addr)
            self._start_cooldown()

    def run(self):
        loop = asyncio.get_event_loop()
        server_coro = asyncio.start_server(self._handle_client_connected, host=self._proxy_ip, port=self._proxy_port)
        server = loop.run_until_complete(server_coro)

        try:
            logger.info("Serving on {}:{}".format(self._proxy_ip, self._proxy_port))
            loop.run_forever()
        except KeyboardInterrupt as e:
            logger.info("Keyboard interrupted. Exiting.")

        server.close()
        loop.run_until_complete(server.wait_closed())
        loop.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--proxy-ip", 
                        type=str, 
                        default="0.0.0.0", 
                        help="Address on which proxy will be listening. Defaults to '0.0.0.0'.")
    parser.add_argument("--proxy-port", 
                        type=int, 
                        default="8000", 
                        help="Port on which proxy will be listening. Defaults to '8000'.")
    parser.add_argument("--target-ip", 
                        type=str, 
                        required=True, 
                        help="Address where to forward requests.")
    parser.add_argument("--target-port", 
                        type=int, 
                        required=True, 
                        help="Port where to forward requests.")
    parser.add_argument("--cooldown-period", 
                        type=int, 
                        default=30, 
                        help="How much time (in minutes) to wait after last client disconnecting before executing cleanup hook.")
    parser.add_argument("--hook-start-svc", 
                        type=str,
                        required=True, 
                        help="Path to an executable that will be executed when the first request comes in.")
    parser.add_argument("--hook-stop-svc", 
                        type=str, 
                        required=True, 
                        help="Path to an executable that will be executed after the cooldown period.")
    args = parser.parse_args()

    server = LifecycleManagingProxyServer(
        args.proxy_ip, 
        args.proxy_port,
        args.target_ip,
        args.target_port,
        args.cooldown_period,
        args.hook_start_svc,
        args.hook_stop_svc)
    server.run()
