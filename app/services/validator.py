import pandas as pd
from fuzzywuzzy import process
from typing import List, Dict, Any, Optional

# Load the product catalog
catalog = pd.read_csv("app/sample_data/Product_Catalog.csv")

class OrderValidator:
    def __init__(self, catalog_df: pd.DataFrame, match_threshold: int = 70):
        """Initialize the validator with a product catalog dataframe
        
        Args:
            catalog_df: DataFrame containing product catalog information
            match_threshold: Minimum score required for a fuzzy match (0-100)
        """
        self.catalog = catalog_df
        self.match_threshold = match_threshold
    
    def validate_order(self, order_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate order items against the product catalog
        
        Args:
            order_items: List of dictionaries containing order items with 'raw_name' and 'quantity'
            
        Returns:
            Dictionary with validated order items and summary information
        """
        validated_items = []
        total_price = 0.0
        total_items = 0
        has_issues = False
        alternative_suggestions = {}
        
        for item in order_items:
            raw_name = item["raw_name"]
            quantity = item["quantity"]
            
            # Find best matches in the catalog
            matches = process.extract(raw_name, self.catalog["Product_Name"], limit=3)
            
            if not matches or len(matches[0]) < 2 or matches[0][1] < self.match_threshold:
                # No good match found
                validated_items.append({
                    "sku": None,
                    "matched_name": None,
                    "requested_name": raw_name,
                    "requested_qty": quantity,
                    "stock": 0,
                    "moq": 0,
                    "price": 0.0,
                    "line_total": 0.0,
                    "match_score": 0,
                    "issue": "Product not found in catalog",
                    "status": "Not Found"
                })
                has_issues = True
                continue
            
            # Get the best match
            best_match_name, score, _ = matches[0]
            matched_row = self.catalog[self.catalog["Product_Name"] == best_match_name].iloc[0]
            
            # Extract product details
            sku = matched_row["Product_Code"]
            stock = matched_row["Available_in_Stock"]
            moq = matched_row["Min_Order_Quantity"]
            price = float(matched_row["Price"])
            description = matched_row.get("Description", "")
            
            # Calculate line total
            line_total = price * quantity
            
            # Check for issues
            issue = None
            status = "Valid"
            
            if stock < quantity:
                issue = f"Insufficient stock (requested: {quantity}, available: {stock})"
                status = "Stock Issue"
                has_issues = True
            elif quantity < moq:
                issue = f"Below minimum order quantity of {moq}"
                status = "MOQ Issue"
                has_issues = True
            
            # Check if this is an ambiguous match (score < 90)
            if score < 90:
                # Get alternative suggestions
                alternatives = []
                for alt_name, alt_score, _ in matches[1:]:  # Skip the best match
                    if alt_score >= self.match_threshold:
                        alt_row = self.catalog[self.catalog["Product_Name"] == alt_name].iloc[0]
                        alternatives.append({
                            "name": alt_name,
                            "sku": alt_row["Product_Code"],
                            "score": alt_score
                        })
                
                if alternatives:
                    alternative_suggestions[raw_name] = alternatives
                    
                    # If match is ambiguous but no other issues, mark as ambiguous
                    if not issue:
                        issue = "Ambiguous match, please verify"
                        status = "Ambiguous"
                        has_issues = True
            
            # Add validated item
            validated_item = {
                "sku": sku,
                "matched_name": best_match_name,
                "requested_name": raw_name,
                "requested_qty": quantity,
                "stock": stock,
                "moq": moq,
                "price": price,
                "line_total": line_total,
                "match_score": score,
                "description": description,
                "issue": issue,
                "status": status
            }
            
            validated_items.append(validated_item)
            
            # Update totals if no stock issues
            if status != "Stock Issue":
                total_items += quantity
                total_price += line_total
        
        # Create the validation summary
        validation_summary = {
            "items": validated_items,
            "total_price": round(total_price, 2),
            "total_items": total_items,
            "has_issues": has_issues,
            "alternative_suggestions": alternative_suggestions
        }
        
        return validation_summary

# Create a singleton validator instance
validator = OrderValidator(catalog)

def validate_order(order_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Validate order items against the product catalog"""
    return validator.validate_order(order_items)