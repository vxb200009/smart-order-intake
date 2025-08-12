import re
from typing import List, Dict, Optional, Any
from datetime import datetime

# Try to load spaCy model, fallback to None if not available
try:
    import spacy
    nlp = spacy.load("en_core_web_sm")
except (ImportError, OSError):
    nlp = None

class OrderItem:
    def __init__(self, quantity: int, raw_name: str):
        self.quantity = quantity
        self.raw_name = raw_name

class OrderDetails:
    def __init__(self):
        self.items: List[OrderItem] = []
        self.delivery_date: Optional[str] = None
        self.shipping_address: Optional[str] = None
        self.customer_name: Optional[str] = None
        self.customer_email: Optional[str] = None
        self.customer_notes: Optional[str] = None
        self.order_id: Optional[str] = None
        self.urgency: Optional[str] = None

class EmailParser:
    def __init__(self):
        self._last_order_details = None
        # Regex patterns for item extraction
        self.item_patterns = [
            # Pattern 1: "9 x Coffee STRÅDAL 620"
            r"[-*]?\s*(\d+)\s*x\s+([^\n]+)",
            
            # Pattern 2: "Bed TRÄNBERG 858 – Qty: 2"
            r"[-*]?\s*([^\n]+?)\s*[–-]\s*(?:Qty|Quantity):\s*(\d+)",
            
            # Pattern 3: "3 units of Bar FJÄRMARK 344"
            r"(\d+)\s+(?:pieces|units?)\s+of\s+([^\n]+)",
            
            # Pattern 4: Simple "Quantity x Product" format
            r"(\d+)\s*x\s+([^\n]+)"
        ]
        
        # Regex patterns for delivery date
        self.date_patterns = [
            r"(?:delivery|deliver|ship|get)\s+(?:by|before|on|to\s+me\s+by)\s+([A-Za-z]+\s+\d{1,2},?\s+\d{4})",
            r"(?:delivery|deliver|ship)\s+(?:date):\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})",
            r"(?:requested\s+delivery\s+date):\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})",
            r"(?:by|before)\s+([A-Za-z]+\s+\d{1,2},?\s+\d{4})"
        ]
        
        # Regex patterns for shipping address
        self.address_patterns = [
            r"(?:ship\s+to|delivery\s+address|send\s+to):\s*([^\n]+(?:\n[^\n]+)*?)(?:\n\n|\n(?=[A-Z])|$)",
            r"(?:ship\s+to|delivery\s+address|send\s+to):\s*([^\n]+)"
        ]
        
        # Regex patterns for customer notes
        self.notes_patterns = [
            r"(?:notes?|comments?|additional\s+information):\s*([^\n]+(?:\n[^\n]+)*)",
            r"(?:please\s+note|note\s+that)\s+([^\n]+(?:\n[^\n]+)*)"
        ]
        
        # Urgency indicators
        self.urgency_keywords = [
            r"urgent", r"asap", r"as soon as possible", r"emergency", 
            r"quickly", r"rush", r"immediate", r"priority"
        ]

    def parse_email(self, email_content: str) -> List[Dict[str, Any]]:
        # Process with spaCy if available
        doc = nlp(email_content) if nlp else None
        
        # Initialize order details
        order = OrderDetails()
        
        # Extract items using regex patterns
        self._extract_items(email_content, order)
        
        # Extract delivery date
        self._extract_delivery_date(email_content, order)
        
        # Extract shipping address and customer name
        self._extract_address_and_name(doc, email_content, order)
        
        # Extract customer notes
        self._extract_customer_notes(email_content, order)
        
        # Detect urgency
        self._detect_urgency(email_content, order)
        
        # Generate a unique order ID
        order.order_id = self.generate_order_id(order.customer_name)
        
        # Store the order details for later retrieval
        self._last_order_details = order
        
        # Convert to dictionary format for compatibility with existing code
        items_dict = []
        for item in order.items:
            items_dict.append({
                "quantity": item.quantity,
                "raw_name": item.raw_name
            })
        
        # Return in the format expected by the validator
        return items_dict
    
    def _extract_items(self, email_content: str, order: OrderDetails) -> None:
        """Extract order items from email content using regex patterns"""
        lines = email_content.splitlines()
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            for pattern in self.item_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    # Handle Pattern 2 differently as quantity is in group 2
                    if "Qty" in line or "Quantity" in line:
                        product_desc = match.group(1).strip()
                        quantity = int(match.group(2))
                    else:
                        quantity = int(match.group(1))
                        product_desc = match.group(2).strip()
                    
                    order.items.append(OrderItem(quantity, product_desc))
                    break
    
    def _extract_delivery_date(self, email_content: str, order: OrderDetails) -> None:
        """Extract delivery date from email content using regex patterns"""
        for pattern in self.date_patterns:
            match = re.search(pattern, email_content, re.IGNORECASE)
            if match:
                order.delivery_date = match.group(1)
                break
    
    def _extract_address_and_name(self, doc, email_content: str, order: OrderDetails) -> None:
        """Extract shipping address and customer name using spaCy NER and regex patterns"""
        # Try to extract address using regex first
        for pattern in self.address_patterns:
            match = re.search(pattern, email_content, re.IGNORECASE)
            if match:
                address_text = match.group(1).strip()
                order.shipping_address = address_text
                break
        
        # Extract customer name using spaCy NER if available
        if doc:
            person_entities = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]
            if person_entities:
                # Use the first person entity as customer name
                order.customer_name = person_entities[0]
        
        # If we couldn't find a name with NER, look for common signature patterns
        if not order.customer_name:
            # Look for name after "Thanks,", "Sincerely,", etc.
            signature_patterns = [
                r"(?:Thanks|Regards|Sincerely|Cheers|Best),?\s*\n\s*([A-Z][a-z]+ [A-Z][a-z]+)",
                r"(?:From|Sent by):?\s*([A-Z][a-z]+ [A-Z][a-z]+)"
            ]
            
            for pattern in signature_patterns:
                match = re.search(pattern, email_content)
                if match:
                    order.customer_name = match.group(1)
                    break
                    
    def generate_order_id(self, customer_name: str = None) -> str:
        """Generate a unique order ID based on timestamp and optional customer name"""
        if customer_name:
            name_part = ''.join(c for c in customer_name if c.isalnum())[:5].upper()
            return f"{name_part}-{datetime.now().strftime('%Y%m%d%H%M')}"
        else:
            return f"ORDER-{datetime.now().strftime('%Y%m%d%H%M')}"
    
    def _extract_customer_notes(self, email_content: str, order: OrderDetails) -> None:
        """Extract customer notes from email content"""
        for pattern in self.notes_patterns:
            match = re.search(pattern, email_content, re.IGNORECASE)
            if match:
                order.customer_notes = match.group(1).strip()
                break
                
        # If no specific notes section found, look for common request phrases
        if not order.customer_notes:
            request_patterns = [
                r"(?:please|kindly)\s+([^.!?\n]+(?:\s+and\s+[^.!?\n]+)?)[.!?]",
                r"(?:would\s+like|need)\s+([^.!?\n]+(?:\s+and\s+[^.!?\n]+)?)[.!?]"
            ]
            
            for pattern in request_patterns:
                match = re.search(pattern, email_content, re.IGNORECASE)
                if match and not any(item_word in match.group(1).lower() for item_word in ["order", "deliver", "ship", "send", "purchase"]):
                    order.customer_notes = match.group(1).strip()
                    break
    
    def _detect_urgency(self, email_content: str, order: OrderDetails) -> None:
        """Detect urgency indicators in the email content"""
        email_lower = email_content.lower()
        
        for keyword in self.urgency_keywords:
            if re.search(r'\b' + keyword + r'\b', email_lower):
                order.urgency = "High"
                return
                
        # Check for date-based urgency (if delivery date is within 7 days)
        if order.delivery_date:
            try:
                # Try to parse the date
                for date_format in ["%B %d, %Y", "%B %d %Y"]:
                    try:
                        delivery_date = datetime.strptime(order.delivery_date, date_format)
                        days_until_delivery = (delivery_date - datetime.now()).days
                        if days_until_delivery < 7 and days_until_delivery >= 0:
                            order.urgency = "Medium"
                        break
                    except ValueError:
                        continue
            except Exception:
                # If date parsing fails, don't set urgency based on date
                pass
                
        # Default urgency is Normal if not set above
        if not order.urgency:
            order.urgency = "Normal"
    
    def get_last_order_details(self) -> Dict:
        """Get the order details from the last parsed email"""
        if hasattr(self, '_last_order_details'):
            order = self._last_order_details
            return {
                "order_id": order.order_id,
                "delivery_date": order.delivery_date,
                "shipping_address": order.shipping_address,
                "customer_name": order.customer_name,
                "customer_email": order.customer_email,
                "customer_notes": order.customer_notes,
                "urgency": order.urgency
            }
        return {}
    
    def _extract_order_details(self, email_content: str) -> Dict:
        """Extract all order details from email content and return as a dictionary"""
        # This method is kept for backward compatibility
        # Parse the email first to populate order details
        self.parse_email(email_content)
        return self.get_last_order_details()

# Create a singleton instance
email_parser = EmailParser()

def parse_email(email: str) -> List[Dict[str, any]]:
    """Parse email content and extract order items"""
    return email_parser.parse_email(email)