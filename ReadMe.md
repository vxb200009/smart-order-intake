# Smart Order Intake System

A FastAPI-based application that extracts order information from unstructured email text, validates orders against a product catalog, and returns structured data for order processing.

## Features

- **Email Parsing**: Extract order items, quantities, delivery dates, shipping addresses, and customer information from unstructured emails using NLP and regex patterns
- **Product Validation**: Match extracted product descriptions to a product catalog using fuzzy matching
- **Order Validation**: Check stock availability and minimum order quantities
- **Ambiguity Resolution**: Identify ambiguous product matches and provide alternatives
- **Order Merging**: Combine multiple orders from different customers or emails
- **API Documentation**: Interactive API documentation with Swagger UI

## Installation

### Prerequisites

- Python 3.9 or higher
- pip (package installer for Python)

### Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/smart-order-intake.git
   cd smart-order-intake
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Download the spaCy English language model:

   ```bash
   python -m spacy download en_core_web_sm
   ```

## Usage

### Starting the Server

```bash
python -m uvicorn app.main:app --reload
```

The server will start at `http://127.0.0.1:8000`

### API Endpoints

#### 1. Parse Email

**Endpoint**: `/parse-email`

**Method**: POST

**Description**: Upload an email file to extract order items and details

**Request**: Form data with a file upload

**Response**: JSON with parsed order details and validation results

#### 2. Validate Order

**Endpoint**: `/validate-order`

**Method**: POST

**Description**: Validate order items against the product catalog

**Request**: JSON array of order items

**Response**: JSON with validation results

#### 3. Merge Orders

**Endpoint**: `/merge-orders`

**Method**: POST

**Description**: Merge multiple orders into a single order

**Request**: JSON array of orders

**Response**: JSON with merged order details and validation results

#### 4. Get Product Catalog

**Endpoint**: `/product-catalog`

**Method**: GET

**Description**: Get the product catalog as JSON

**Response**: JSON with product catalog

### API Documentation

Interactive API documentation is available at:

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## Architecture

### Components

1. **Email Parser**: Uses spaCy NLP and regex patterns to extract structured data from unstructured emails
2. **Order Validator**: Validates extracted order items against a product catalog using fuzzy matching
3. **FastAPI Application**: Provides RESTful API endpoints for email parsing, order validation, and order merging

### Data Flow

1. User uploads an email file to the `/parse-email` endpoint
2. The email parser extracts order items, delivery date, shipping address, and customer information
3. The order validator matches extracted items to products in the catalog
4. The API returns structured data with validation results

## License

MIT
