# backend/logger_setup.py
# api/logger_setup.py
# Sets up a logger that prints activity happening on the server side.
# This helps us see what the server is doing behind the scenes during a request.

import logging
import sys

logging.basicConfig(
    level=logging.INFO,                                                            
    format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
    stream=sys.stdout                                                              
)

logger = logging.getLogger(__name__)  