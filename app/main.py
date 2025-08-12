from fastapi import FastAPI, File, UploadFile, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from typing import List, Dict, Any, Optional
import json

from app.services.email_parser import parse_email, email_parser
from app.services.validator import validate_order

app = FastAPI(
    title="Smart Order Intake API",
    description="API for parsing and validating order emails",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Smart Order Intake API is running"}

@app.post("/parse-email", summary="Parse and validate an email order")
async def upload_email(file: UploadFile = File(...)):
    """Parse an email file and validate the order against the product catalog.
    
    Returns a JSON with parsed order details and validation results.
    """
    try:
        # Read the email content
        email_content = await file.read()
        email_text = email_content.decode("utf-8")
        
        # Parse the email to extract order items
        parsed_items = parse_email(email_text)
        
        # Get additional order details from the last parse
        order_details = email_parser.get_last_order_details()
        
        # Validate the order against the product catalog
        validation_results = validate_order(parsed_items)
        
        # Combine order details with validation results
        response = {
            "order_details": order_details,
            "validation_results": validation_results
        }
        
        return JSONResponse(content=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/validate-order", summary="Validate an order without email parsing")
async def validate_order_items(order_items: List[Dict[str, Any]] = Body(...)):
    """Validate order items against the product catalog.
    
    This endpoint allows validating orders without email parsing.
    """
    try:
        # Validate the order against the product catalog
        validation_results = validate_order(order_items)
        return {"validation_results": validation_results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/merge-orders", summary="Merge multiple orders")
async def merge_orders(orders: List[Dict[str, Any]] = Body(...)):
    """Merge multiple orders into a single order.
    
    This is useful for combining orders from different customers or emails.
    """
    try:
        # Initialize merged order
        merged_items = {}
        merged_details = {
            "order_id": f"MERGED-{email_parser.generate_order_id()}",
            "customer_names": [],
            "shipping_addresses": [],
            "delivery_dates": [],
            "urgency": "Normal"
        }
        
        # Merge orders
        for order in orders:
            # Merge order details
            if "order_details" in order:
                details = order["order_details"]
                if details.get("customer_name") and details["customer_name"] not in merged_details["customer_names"]:
                    merged_details["customer_names"].append(details["customer_name"])
                if details.get("shipping_address") and details["shipping_address"] not in merged_details["shipping_addresses"]:
                    merged_details["shipping_addresses"].append(details["shipping_address"])
                if details.get("delivery_date") and details["delivery_date"] not in merged_details["delivery_dates"]:
                    merged_details["delivery_dates"].append(details["delivery_date"])
                if details.get("urgency") == "High":
                    merged_details["urgency"] = "High"
            
            # Merge validation results
            if "validation_results" in order and "items" in order["validation_results"]:
                for item in order["validation_results"]["items"]:
                    sku = item["sku"]
                    if not sku:  # Skip items without SKU
                        continue
                        
                    if sku in merged_items:
                        # Add quantities
                        merged_items[sku]["requested_qty"] += item["requested_qty"]
                        merged_items[sku]["line_total"] = merged_items[sku]["price"] * merged_items[sku]["requested_qty"]
                        
                        # Update status if there's an issue
                        if item["status"] != "Valid" and merged_items[sku]["status"] == "Valid":
                            merged_items[sku]["status"] = item["status"]
                            merged_items[sku]["issue"] = item["issue"]
                    else:
                        # Add new item
                        merged_items[sku] = item.copy()
        
        # Convert merged items dict to list
        merged_items_list = list(merged_items.values())
        
        # Calculate totals
        total_price = sum(item["line_total"] for item in merged_items_list if item["status"] != "Stock Issue")
        total_items = sum(item["requested_qty"] for item in merged_items_list if item["status"] != "Stock Issue")
        
        # Check if there are any issues
        has_issues = any(item["status"] != "Valid" for item in merged_items_list)
        
        # Create merged validation results
        merged_validation = {
            "items": merged_items_list,
            "total_price": round(total_price, 2),
            "total_items": total_items,
            "has_issues": has_issues
        }
        
        return {
            "order_details": merged_details,
            "validation_results": merged_validation
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

