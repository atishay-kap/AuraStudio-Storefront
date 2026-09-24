import os
import razorpay
from dotenv import load_dotenv

load_dotenv()

key_id = os.getenv("RAZORPAY_KEY_ID", "rzp_test_placeholder")
key_secret = os.getenv("RAZORPAY_KEY_SECRET", "secret_placeholder")

client = razorpay.Client(
    auth=(key_id, key_secret)
)