import logging
import imaplib
import email
import os
from email.header import decode_header
from collections import defaultdict
from fuzzywuzzy import fuzz
from podcastfy.utils.config import Config

logger = logging.getLogger(__name__)

class BookmarkManager:
	def __init__(self, email_address, password, imap_server="imap.gmail.com", attachment_dir="attachments", similarity_threshold=80):
		"""
		Initialize the BookmarkManager.

		Args:
			email_address (str): The email address to connect to.
			password (str): The password for the email account.
			imap_server (str, optional): The IMAP server address. Defaults to "imap.gmail.com".
			attachment_dir (str, optional): Directory to save PDF attachments. Defaults to "attachments".
			similarity_threshold (int, optional): Threshold for fuzzy matching of subjects. Defaults to 80.

		Note:
			The resulting structure of the bookmarks dictionary will be:
			{
				"sender1@example.com": {
					"Subject 1": {
						"links": ["link1", "link2"],
						"pdfs": ["path/to/pdf1.pdf", "path/to/pdf2.pdf"]
					},
					"Subject 2": {
						"links": ["link3", "link4"],
						"pdfs": []
					}
				},
				"sender2@example.com": {
					"Subject 3": {
						"links": ["link5", "link6"],
						"pdfs": ["path/to/pdf3.pdf"]
					},
					"No Subject": {
						"links": ["link7"],
						"pdfs": []
					}
				}
			}
		"""
		self.email_address = email_address
		self.password = password
		self.imap_server = imap_server
		self.attachment_dir = attachment_dir
		self.similarity_threshold = similarity_threshold
		os.makedirs(self.attachment_dir, exist_ok=True)

	def fetch_bookmarks(self):
		"""
		Fetch bookmarks (links and PDF attachments) from the email inbox, grouped by sender and subject.

		Returns:
			dict: A nested dictionary of bookmarks grouped by sender and subject.
		"""
		bookmarks = defaultdict(lambda: defaultdict(lambda: {"links": [], "pdfs": []}))
		try:
			with imaplib.IMAP4_SSL(self.imap_server) as mail:
				mail.login(self.email_address, self.password)
				mail.select("inbox")
				_, message_numbers = mail.search(None, "ALL")
				for num in message_numbers[0].split():
					_, msg = mail.fetch(num, "(RFC822)")
					email_message = email.message_from_bytes(msg[0][1])
					sender = self.get_sender(email_message)
					subject = self.get_subject(email_message)
					links = self.extract_links(email_message)
					pdfs = self.extract_pdf_attachments(email_message)
					
					# Use fuzzy matching for subject
					matched_subject = self.fuzzy_match_subject(bookmarks[sender], subject)
					bookmarks[sender][matched_subject]["links"].extend(links)
					bookmarks[sender][matched_subject]["pdfs"].extend(pdfs)
		except Exception as e:
			logger.error(f"Error fetching bookmarks: {str(e)}")
			raise
		return dict(bookmarks)

	def fuzzy_match_subject(self, sender_bookmarks, new_subject):
		"""
		Find the best matching subject using fuzzy string matching.

		Args:
			sender_bookmarks (dict): Existing bookmarks for the sender.
			new_subject (str): The subject to match.

		Returns:
			str: The best matching subject or the new subject if no match is found.
		"""
		if not sender_bookmarks:
			return new_subject

		best_match = max(sender_bookmarks.keys(),
						 key=lambda x: fuzz.ratio(x.lower(), new_subject.lower()))
		
		if fuzz.ratio(best_match.lower(), new_subject.lower()) >= self.similarity_threshold:
			return best_match
		return new_subject

	def get_sender(self, email_message):
		"""
		Extract the sender's email address from the email message.

		Args:
			email_message (email.message.Message): The email message object.

		Returns:
			str: The sender's email address.
		"""
		sender, encoding = decode_header(email_message["From"])[0]
		if isinstance(sender, bytes):
			sender = sender.decode(encoding or "utf-8")
		return sender.split("<")[-1].strip(">")

	def get_subject(self, email_message):
		"""
		Extract the subject from the email message.

		Args:
			email_message (email.message.Message): The email message object.

		Returns:
			str: The email subject.
		"""
		subject, encoding = decode_header(email_message["Subject"])[0]
		if isinstance(subject, bytes):
			subject = subject.decode(encoding or "utf-8")
		return subject or "No Subject"

	def extract_links(self, email_message):
		"""
		Extract links from the email message.

		Args:
			email_message (email.message.Message): The email message object.

		Returns:
			list: A list of extracted links.
		"""
		links = []
		if email_message.is_multipart():
			for part in email_message.walk():
				if part.get_content_type() == "text/plain":
					body = part.get_payload(decode=True).decode()
					links.extend(self.find_links(body))
		else:
			body = email_message.get_payload(decode=True).decode()
			links.extend(self.find_links(body))
		return links

	def find_links(self, text):
		"""
		Find links in the given text using a robust regex pattern.

		Args:
			text (str): The text to search for links.

		Returns:
			list: A list of found links.
		"""
		import re

		# Regex pattern to match various URL formats
		url_pattern = re.compile(r"""
			(https?://)?  # Optional http:// or https://
			([\w-]+\.)+  # Domain name
			[\w-]+  # Top-level domain
			(/[\w./?%&=+-]*)?  # Optional path and query parameters
		""", re.VERBOSE | re.IGNORECASE)

		# Find all matches in the text
		links = url_pattern.findall(text)

		# Process the matches to get complete URLs
		complete_links = []
		for link in links:
			full_link = ''.join(link)
			if not full_link.startswith(('http://', 'https://')):
				full_link = 'http://' + full_link
			complete_links.append(full_link)

		return complete_links

	def extract_pdf_attachments(self, email_message):
		"""
		Extract PDF attachments from the email message.

		Args:
			email_message (email.message.Message): The email message object.

		Returns:
			list: A list of saved PDF file paths.
		"""
		pdf_files = []
		for part in email_message.walk():
			if part.get_content_maintype() == "application" and part.get_content_subtype() == "pdf":
				filename = part.get_filename()
				if filename:
					filepath = os.path.join(self.attachment_dir, filename)
					with open(filepath, "wb") as f:
						f.write(part.get_payload(decode=True))
					pdf_files.append(filepath)
		return pdf_files

def main():
	# Set up logging
	logging.basicConfig(level=logging.INFO)

	# Load configuration
	config = Config()

	# Create an instance of BookmarkManager
	bookmark_manager = BookmarkManager(
		email_address=config.EMAIL_ADDRESS,
		password=config.EMAIL_PASSWORD,
		attachment_dir="test_attachments"
	)

	try:
		# Fetch bookmarks
		bookmarks = bookmark_manager.fetch_bookmarks()

		# Print a summary of the fetched bookmarks
		logger.info("Fetched bookmarks summary:")
		for sender, subjects in bookmarks.items():
			logger.info(f"Sender: {sender}")
			for subject, content in subjects.items():
				logger.info(f"  Subject: {subject}")
				logger.info(f"    Links: {len(content['links'])}")
				logger.info(f"    PDFs: {len(content['pdfs'])}")

		# Print the first link and PDF (if any) for each sender and subject
		logger.info("\nSample content:")
		for sender, subjects in bookmarks.items():
			for subject, content in subjects.items():
				if content['links']:
					logger.info(f"Sample link from {sender} - {subject}: {content['links'][0]}")
				if content['pdfs']:
					logger.info(f"Sample PDF from {sender} - {subject}: {content['pdfs'][0]}")

	except Exception as e:
		logger.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
	main()