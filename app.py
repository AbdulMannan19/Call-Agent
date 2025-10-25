from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import asyncio
import threading
import json
from datetime import datetime
from voice_call import AudioLoop
from sql_utils import SupabaseFoodOrderingTools
from config import SYSTEM_PROMPT

app = Flask(__name__)
app.config['SECRET_KEY'] = 'food-ordering-bot-secret-key-2024'
socketio = SocketIO(app, cors_allowed_origins="*")

class WebVoiceBot:
    def __init__(self):
        """Initialize the web voice bot"""
        self.db_tools = SupabaseFoodOrderingTools()
        self.current_customer_phone = "+1234567890"
        self.function_declarations = self._create_function_declarations()
        self.audio_loop = None
        self.is_running = False
        
    def _create_function_declarations(self):
        """Create function declarations for Gemini function calling"""
        return [
            {
                "name": "get_menu_items",
                "description": "Fetch available menu items, optionally filtered by category",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "Optional category filter (Mains, Beverages, Sides, Desserts)"
                        }
                    }
                }
            },
            {
                "name": "create_order",
                "description": "Create a new order with items and return order_id",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "items": {
                            "type": "object",
                            "description": "Dictionary mapping item_id to quantity"
                        },
                        "special_requests": {
                            "type": "string",
                            "description": "Optional special requests from customer"
                        }
                    },
                    "required": ["items"]
                }
            },
            {
                "name": "create_delivery",
                "description": "Create delivery record for an order",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_id": {
                            "type": "integer",
                            "description": "ID of the order to create delivery for"
                        },
                        "delivery_address": {
                            "type": "string",
                            "description": "Customer's delivery address"
                        }
                    },
                    "required": ["order_id", "delivery_address"]
                }
            },
            {
                "name": "get_order_status",
                "description": "Get order status and details by customer phone number",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "phone_number": {
                            "type": "string",
                            "description": "Customer's phone number"
                        }
                    },
                    "required": ["phone_number"]
                }
            }
        ]
    
    async def _handle_function_call(self, function_name: str, arguments: dict) -> any:
        """Handle function calls and emit to frontend"""
        try:
            # Emit function call to frontend
            socketio.emit('function_call', {
                'function_name': function_name,
                'arguments': arguments,
                'timestamp': datetime.now().strftime('%H:%M:%S')
            })
            
            result = None
            
            if function_name == "get_menu_items":
                category = arguments.get("category")
                result = self.db_tools.get_menu_items(category)
                
            elif function_name == "create_order":
                items = arguments.get("items", {})
                if hasattr(items, '_pb') or 'MapComposite' in str(type(items)):
                    items = dict(items)
                special_requests = arguments.get("special_requests")
                result = self.db_tools.create_order(items, special_requests)
                
            elif function_name == "create_delivery":
                order_id = arguments.get("order_id")
                delivery_address = arguments.get("delivery_address")
                result = self.db_tools.create_delivery(order_id, delivery_address, self.current_customer_phone)
                
            elif function_name == "get_order_status":
                phone_number = arguments.get("phone_number")
                result = self.db_tools.get_order_status(phone_number)
            
            # Emit function result to frontend
            socketio.emit('function_result', {
                'function_name': function_name,
                'result': result,
                'timestamp': datetime.now().strftime('%H:%M:%S')
            })
            
            return result
            
        except Exception as e:
            error_msg = f"Error executing {function_name}: {str(e)}"
            socketio.emit('function_error', {
                'function_name': function_name,
                'error': error_msg,
                'timestamp': datetime.now().strftime('%H:%M:%S')
            })
            return error_msg

# Initialize bot
web_bot = WebVoiceBot()

@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print('Client connected')
    emit('status', {'message': 'Connected to voice bot'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print('Client disconnected')

@socketio.on('start_voice')
def handle_start_voice():
    """Start voice bot"""
    if not web_bot.is_running:
        web_bot.is_running = True
        emit('status', {'message': 'Voice bot started - speak now!'})
        # Note: In a real implementation, you'd start the audio loop here
        # For now, we'll simulate it
        emit('bot_response', {
            'text': 'Hello! Welcome to our food ordering service. How can I help you today?',
            'timestamp': datetime.now().strftime('%H:%M:%S')
        })

@socketio.on('stop_voice')
def handle_stop_voice():
    """Stop voice bot"""
    web_bot.is_running = False
    emit('status', {'message': 'Voice bot stopped'})

@socketio.on('simulate_user_input')
def handle_simulate_input(data):
    """Simulate user input for testing"""
    user_text = data.get('text', '')
    emit('user_input', {
        'text': user_text,
        'timestamp': datetime.now().strftime('%H:%M:%S')
    })
    
    # Simulate bot processing and function calls
    if 'menu' in user_text.lower():
        # Simulate function call
        asyncio.run(web_bot._handle_function_call('get_menu_items', {}))
        emit('bot_response', {
            'text': 'Here are our available menu items. What would you like to order?',
            'timestamp': datetime.now().strftime('%H:%M:%S')
        })

if __name__ == '__main__':
    socketio.run(app, debug=True, host='localhost', port=5000)