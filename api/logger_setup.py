# backend/logger_setup.py
# api/logger_setup.py
# Sets up a logger that prints activity happening on the server side.
# This helps us see what the server is doing behind the scenes during a request.

import sys, os; sys.path.insert(0, os.path.dirname(__file__))  # ensures sibling imports work on Vercel
import logging
import sys

logging.basicConfig(
    level=logging.INFO,                                                               # log INFO level and above
    format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",  # timestamp + file + line number
    stream=sys.stdout                                                                 # print logs to the terminal
)

logger = logging.getLogger(__name__)  # create a logger instance to use across the app