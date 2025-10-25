import os
from dotenv import load_dotenv
from supabase import create_client, Client
from typing import Optional, Dict, Any, List
import json

load_dotenv()

class SupabaseFoodOrderingTools:
    def __init__(self):
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment variables")
        
        self.supabase: Client = create_client(supabase_url, supabase_key)
    
    def get_menu_items(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            query = self.supabase.table('menu').select('*').eq('is_available', True)
            
            if category:
                query = query.eq('category', category)
            
            response = query.execute()
            return response.data
            
        except Exception as e:
            print(f"Error fetching menu items: {e}")
            return []
    
    def create_order(self, items: Dict[str, int], special_requests: Optional[str] = None) -> Optional[int]:
        try:
            total_amount = 0
            for item_id, quantity in items.items():
                menu_item = self.supabase.table('menu').select('price').eq('item_id', item_id).execute()
                if menu_item.data:
                    price = float(menu_item.data[0]['price'])
                    total_amount += price * quantity
                else:
                    print(f"Item {item_id} not found in menu")
                    return None
            
            # Ensure items is a regular dict and convert keys to strings
            if hasattr(items, '_pb') or 'MapComposite' in str(type(items)):
                items = dict(items)
            
            # Convert all keys to strings for JSON serialization
            items_dict = {str(k): int(v) for k, v in items.items()}
            
            order_data = {
                'items': json.dumps(items_dict),  # Store as JSONB
                'total_amount': total_amount,
                'special_requests': special_requests
            }
            
            response = self.supabase.table('orders').insert(order_data).execute()
            
            if response.data:
                return response.data[0]['order_id']
            return None
            
        except Exception as e:
            print(f"Error creating order: {e}")
            return None
    
    def create_delivery(self, order_id: int, delivery_address: str, customer_phone_number: str) -> bool:
        try:
            
            delivery_data = {
                'order_id': order_id,
                'delivery_address': delivery_address,
                'status': 'PREPARING',
                'customer_phone_number': customer_phone_number
            }
            
            response = self.supabase.table('deliveries').insert(delivery_data).execute()
            return len(response.data) > 0
            
        except Exception as e:
            print(f"Error creating delivery: {e}")
            return False
    
    def get_order_status(self, phone_number: str) -> List[Dict[str, Any]]:
        try:
            # Query deliveries by phone number and join with orders
            response = self.supabase.table('deliveries').select(
                '*, orders(*)'
            ).eq('customer_phone_number', phone_number).execute()
            
            return response.data
            
        except Exception as e:
            print(f"Error fetching order status: {e}")
            return []

