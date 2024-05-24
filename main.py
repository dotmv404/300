import asyncio
import ssl
import json
import time
import uuid
from datetime import datetime, timedelta, time as datetime_time
from loguru import logger
from keep_alive import keep_alive
from websockets_proxy import Proxy, proxy_connect
import requests  # Added to fetch the proxy list

keep_alive()

# Configurable time window (UTC)
START_TIME = datetime_time(12, 0)  # 9:00 AM UTC
END_TIME = datetime_time(1, 20)  # 9:17 AM UTC
PROXY_URL = "https://raw.githubusercontent.com/dotmv404/items/main/50.txt"

async def connect_to_wss(socks5_proxy, user_id, stop_event):
    device_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, socks5_proxy))
    logger.info(f"Device ID: {device_id}")
    custom_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    }
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    uri = "wss://proxy.wynd.network:4650/"
    server_hostname = "proxy.wynd.network"
    proxy = Proxy.from_url(socks5_proxy)

    while not stop_event.is_set():
        try:
            async with proxy_connect(uri, proxy=proxy, ssl=ssl_context, server_hostname=server_hostname,
                                     extra_headers=custom_headers) as websocket:
                async def send_ping():
                    while not stop_event.is_set():
                        try:
                            send_message = json.dumps(
                                {"id": str(uuid.uuid4()), "version": "1.0.0", "action": "PING", "data": {}})
                            logger.debug(f"Sending PING: {send_message}")
                            await websocket.send(send_message)
                            await asyncio.sleep(20)
                        except Exception as e:
                            logger.error(f"Error in send_ping: {e}")
                            break

                # Start the ping task after connection is established
                ping_task = asyncio.create_task(send_ping())

                async for response in websocket:
                    if stop_event.is_set():
                        break
                    message = json.loads(response)
                    logger.info(f"Received message: {message}")
                    if message.get("action") == "AUTH":
                        auth_response = {
                            "id": message["id"],
                            "origin_action": "AUTH",
                            "result": {
                                "browser_id": device_id,
                                "user_id": user_id,
                                "user_agent": custom_headers['User-Agent'],
                                "timestamp": int(time.time()),
                                "device_type": "extension",
                                "version": "2.5.0"
                            }
                        }
                        logger.debug(f"Sending AUTH response: {auth_response}")
                        await websocket.send(json.dumps(auth_response))

                    elif message.get("action") == "PONG":
                        pong_response = {"id": message["id"], "origin_action": "PONG"}
                        logger.debug(f"Sending PONG response: {pong_response}")
                        await websocket.send(json.dumps(pong_response))
        except Exception as e:
            if not stop_event.is_set():
                logger.error(f"Error: {e}")
                logger.error(f"Proxy: {socks5_proxy}")
                # Add a delay before retrying the connection
                await asyncio.sleep(5)

async def main():
    _user_id = '2gc4cjZQnpmLNCHcca6GkU4Bfyy'
    
    # Fetch the proxy list from the URL
    response = requests.get(PROXY_URL)
    response.raise_for_status()  # Ensure we notice bad responses
    socks5_proxy_list = [line.strip() for line in response.text.splitlines() if line.strip()]

    stop_event = asyncio.Event()
    
    while True:
        current_time = datetime.utcnow().time()
        
        # Adjust the time window condition to handle the overnight period correctly
        if (START_TIME <= current_time < datetime_time(23, 59, 59)) or (datetime_time(0, 0) <= current_time < END_TIME):
            logger.info(f"Current time is {current_time}. Within the run window.")
            connection_tasks = [asyncio.create_task(connect_to_wss(proxy, _user_id, stop_event)) for proxy in socks5_proxy_list]
            await asyncio.sleep((datetime.combine(datetime.utcnow().date(), END_TIME) - datetime.utcnow()).total_seconds())
            stop_event.set()
            await asyncio.gather(*connection_tasks)
            stop_event.clear()
        else:
            next_run_time = datetime.combine(datetime.utcnow().date(), START_TIME)
            if current_time >= END_TIME:
                next_run_time += timedelta(days=1)
            sleep_seconds = (next_run_time - datetime.utcnow()).total_seconds()
            logger.info(f"Current time is {datetime.utcnow()}. Sleeping for {sleep_seconds} seconds until the next run window.")
            await asyncio.sleep(min(sleep_seconds, 2 * 60))  # Check again in 2 minutes or when the next run window starts, whichever is sooner

if __name__ == '__main__':
    asyncio.run(main())
