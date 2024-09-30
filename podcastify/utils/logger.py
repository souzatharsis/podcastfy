import logging

def setup_logger(name):
	logger = logging.getLogger(name)
	logger.setLevel(logging.INFO)
	
	formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
	
	console_handler = logging.StreamHandler()
	console_handler.setFormatter(formatter)
	
	logger.addHandler(console_handler)
	
	return logger