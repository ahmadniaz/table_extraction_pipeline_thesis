# Commission Tracker Server

## Setup Instructions

### 1. Environment Variables
Create a `.env` file in the server directory with the following variables:

```env
# Supabase Database URL
# Format: postgresql+asyncpg://postgres:[YOUR-PASSWORD]@[YOUR-PROJECT-REF].supabase.co:5432/postgres
SUPABASE_DB_KEY=postgresql+asyncpg://postgres:[YOUR-PASSWORD]@[YOUR-PROJECT-REF].supabase.co:5432/postgres

# AWS Credentials (if using AWS Textract)
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_DEFAULT_REGION=us-east-1
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Server
```bash
uvicorn app.main:app --reload
```

The server will run on http://localhost:8000

## API Endpoints

- `GET /companies/` - List all companies
- `POST /companies/` - Create a new company
- `GET /companies/{company_id}/mapping/` - Get company field mappings
- `POST /companies/{company_id}/mapping/` - Update company field mappings

## Database Schema

The application automatically creates the following tables on startup:
- `companies` - Company information
- `company_field_mappings` - Field mappings for each company
- `statement_uploads` - Uploaded statement data 