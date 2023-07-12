'''Collection of utility functions related to logging.'''

import logging
import logging.handlers
import os
import sys

from typing import TextIO

def is_docker() -> bool:
    '''Checks if the application is being run within a Docker container.'''

    path = '/proc/self/cgroup'
    return os.path.exists('/.dockerenv') or (os.path.isfile(path) and any('docker' in line for line in open(path, encoding='utf-8')))


def stream_supports_color(stream: TextIO) -> bool:
    '''Checks if the provided `TextIO` stream supports color.'''

    is_a_tty = hasattr(stream, 'isatty') and stream.isatty()

    if 'PYCHARM_HOSTED' in os.environ or os.environ.get('TERM_PROGRAM') == 'vscode':
        return is_a_tty

    if sys.platform != 'win32':
        return is_a_tty or is_docker()

    return is_a_tty and ('ANSICON' in os.environ or 'WT_SESSION' in os.environ)


class ColorFormatter(logging.Formatter):
    '''A logging formatter that applies colored formatting to logs.'''

    LEVEL_COLORS = [
        (logging.DEBUG, '\x1b[40;1m'),
        (logging.INFO, '\x1b[34;1m'),
        (logging.WARNING, '\x1b[33;1m'),
        (logging.ERROR, '\x1b[31m'),
        (logging.CRITICAL, '\x1b[41m'),
    ]

    FORMATS = {
        level: logging.Formatter(
            f'\x1b[30;1m%(asctime)s\x1b[0m {color}%(levelname)-8s\x1b[0m \x1b[35m%(name)s\x1b[0m %(message)s',
            '%Y-%m-%d %H:%M:%S',
        )
        for level, color in LEVEL_COLORS
    }

    def format(self, record: logging.LogRecord) -> str:
        formatter = self.FORMATS.get(record.levelno)
        if formatter is None:
            formatter = self.FORMATS[logging.DEBUG]

        if record.exc_info:
            text = formatter.formatException(record.exc_info)
            record.exc_text = f'\x1b[31m{text}\x1b[0m'

        output = formatter.format(record)

        record.exc_text = None
        return output


def setup_logging(file_log_level: int=logging.INFO, stream_log_level: int=logging.INFO) -> None:
    '''Sets up logging handlers for both console and file logging.'''

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    dt_fmt = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')

    file_max_size = 10 * 1024 * 1024 # 10mb

    file_handler = logging.handlers.RotatingFileHandler(filename='bot.log', encoding='utf-8', maxBytes=file_max_size, backupCount=1)
    file_handler.setLevel(file_log_level)
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(stream_log_level)

    if stream_supports_color(stream_handler.stream):
        formatter = ColorFormatter()

    stream_handler.setFormatter(formatter)

    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)
