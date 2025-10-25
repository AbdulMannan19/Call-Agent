import asyncio
from typing import Dict, Any
from voice_call import AudioLoop
from sql_tools import SupabaseFoodOrderingTools
from config import SYSTEM_PROMPT

class FoodOrderingVoiceBot:
    def __init__(self):
        """Initialize the food ordering voice bot"""
        # Initialize database tools
        self.db_tools = SupabaseFoodOrderingTools()
        
        # Current customer phone number (set when call starts)
        self.current_customer_phone = "+1234567890"  # Default for testing
        
        # Create function declarations for Gemini
        self.function_declarations = self._create_function_declarations()
        
        # Initialize audio loop with system prompt, tools, and function handler
        self.audio_loop = AudioLoop(
            system_prompt=SYSTEM_PROMPT,
            tools=self.function_declarations,
            function_handler=self._handle_function_call
        )
    
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
    
    async def _handle_function_call(self, function_name: str, arguments: Dict[str, Any]) -> Any:
        """Handle function calls from Gemini"""
        try:
            print(f"Executing function: {function_name} with args: {arguments}")
            
            if function_name == "get_menu_items":
                category = arguments.get("category")
                return self.db_tools.get_menu_items(category)
            
            elif function_name == "create_order":
                items = arguments.get("items", {})
                print(f"Items type: {type(items)}, Items value: {items}")
                
                # Convert MapComposite to regular dict if needed
                if hasattr(items, '_pb') or 'MapComposite' in str(type(items)):
                    items = dict(items)
                    print(f"Converted items: {items}")
                
                special_requests = arguments.get("special_requests")
                return self.db_tools.create_order(items, special_requests)
            
            elif function_name == "create_delivery":
                order_id = arguments.get("order_id")
                delivery_address = arguments.get("delivery_address")
                return self.db_tools.create_delivery(order_id, delivery_address, self.current_customer_phone)
            
            elif function_name == "get_order_status":
                phone_number = arguments.get("phone_number")
                return self.db_tools.get_order_status(phone_number)
            
            else:
                return f"Unknown function: {function_name}"
                
        except Exception as e:
            print(f"Error executing {function_name}: {str(e)}")
            return f"Error executing {function_name}: {str(e)}"
    
    def set_customer_phone(self, phone_number: str):
        """Set the current customer's phone number"""
        self.current_customer_phone = phone_number
        print(f"Customer phone number set to: {phone_number}")
    
    async def start(self):
        """Start the voice bot"""
        print("Starting Food Ordering Voice Bot...")
        print(f"Customer phone: {self.current_customer_phone}")
        print("Speak to place your order!")
        
        await self.audio_loop.run()

# Main execution
if __name__ == "__main__":
    print("Food Ordering Voice Bot Started")
    bot = FoodOrderingVoiceBot()
    try:
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        print("\nGoodbye!")