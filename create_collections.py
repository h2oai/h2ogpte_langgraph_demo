#!/usr/bin/env python3
"""
Script to create h2oGPTe collections for the credit renewal workflow.

This script creates three collections:
1. Policy Collection - Contains credit policy and underwriting guidelines
2. Entity Collection - Contains borrower financial data and risk profiles
3. Market Collection - Contains market conditions and sector analysis

Run this script after setting up your .env file with H2OGPTE_API_KEY.
"""

import os

from dotenv import load_dotenv
from h2ogpte import H2OGPTE

# Load environment variables
load_dotenv()


def main():
    """Create collections for the credit renewal workflow."""

    # Initialize h2oGPTe client
    client = H2OGPTE(
        address=os.getenv("H2OGPTE_URL", "https://h2ogpte.genai.h2o.ai"),
        api_key=os.getenv("H2OGPTE_API_KEY")
    )

    if not os.getenv("H2OGPTE_API_KEY"):
        raise ValueError(
            "H2OGPTE_API_KEY environment variable not set. "
            "Please check the README for setup instructions and ensure your .env file is configured correctly."
        )

    print("🔍 Checking existing collections...")
    existing_collections = {c.name: c.id for c in client.list_recent_collections(0, 1000)}

    # Define collections to create for the credit renewal workflow
    collections_to_create = {
        "Policy Collection": {
            "description": "Credit policy and underwriting guidelines for loan renewals",
            "documents": [
                "references/policy_docs/credit_policy.json",
                "references/policy_docs/covenant_library.json",
                "references/policy_docs/rating_methodology.json",
                "references/policy_docs/exemplar_memo.json"
            ]
        },
        "Entity Collection": {
            "description": "Borrower financial data, credit history, and risk profiles",
            "documents": [
                "references/entity_docs/borrower_profile.json",
                "references/entity_docs/financial_statements.json",
                "references/entity_docs/customer_market_position.json",
                "references/entity_docs/facility_covenant.json"
            ]
        },
        "Market Collection": {
            "description": "Market conditions, sector analysis, and economic indicators",
            "documents": [
                "references/market_docs/sector_analysis.json",
                "references/market_docs/economic_outlook.json",
                "references/market_docs/competitive_intelligence.json"
            ]
        }
    }

    created_collections = {}

    for collection_name, config in collections_to_create.items():
        print(f"\n📁 Processing {collection_name}...")

        # Check if collection already exists
        if collection_name in existing_collections:
            collection_id = existing_collections[collection_name]
            print(f"   ✅ Collection already exists: {collection_id}")
            created_collections[collection_name] = collection_id
            continue

        # Create new collection
        try:
            collection_id = client.create_collection(
                name=collection_name,
                description=config["description"]
            )
            print(f"   ✅ Created collection: {collection_id}")

            # Upload and ingest documents
            uploaded_files = []
            for doc_path in config["documents"]:
                if os.path.exists(doc_path):
                    print(f"   📄 Uploading: {doc_path}")
                    # Upload the file first
                    with open(doc_path, "rb") as f:
                        upload_id = client.upload(os.path.basename(doc_path), f)
                        uploaded_files.append(upload_id)
                        print(f"   ✅ Uploaded: {upload_id}")
                else:
                    print(f"   ⚠️  File not found: {doc_path}")

            # Ingest all uploaded files into the collection
            if uploaded_files:
                print(f"   📄 Ingesting {len(uploaded_files)} files into collection...")
                client.ingest_uploads(
                    collection_id=collection_id,
                    upload_ids=uploaded_files
                )
                print(f"   ✅ Ingested {len(uploaded_files)} files")

            created_collections[collection_name] = collection_id

        except Exception as e:
            print(f"   ❌ Error creating {collection_name}: {str(e)}")

    # Update .env file with new collection IDs
    env_file_path = ".env"
    if os.path.exists(env_file_path):
        print("\n📝 Updating .env file with new collection IDs...")

        # Read current .env file
        with open(env_file_path, 'r') as f:
            lines = f.readlines()

        # Update collection IDs in the file
        updated_lines = []
        for line in lines:
            if line.startswith("POLICY_COLLECTION_ID="):
                updated_lines.append(f"POLICY_COLLECTION_ID={created_collections.get('Policy Collection', '')}\n")
            elif line.startswith("ENTITY_COLLECTION_ID="):
                updated_lines.append(f"ENTITY_COLLECTION_ID={created_collections.get('Entity Collection', '')}\n")
            elif line.startswith("MARKET_COLLECTION_ID="):
                updated_lines.append(f"MARKET_COLLECTION_ID={created_collections.get('Market Collection', '')}\n")
            else:
                updated_lines.append(line)

        # Write updated .env file
        with open(env_file_path, 'w') as f:
            f.writelines(updated_lines)

        print("   ✅ Updated .env file with new collection IDs")
    else:
        print("\n⚠️  .env file not found. Please copy from .env.example and run the script again.")
        print("\n📋 Collection IDs to add to your .env file:")
        print("# Collection IDs for RAG queries")
        for name, collection_id in created_collections.items():
            env_var_name = name.upper().replace(" ", "_") + "_ID"
            print(f"{env_var_name}={collection_id}")

    # Print summary
    print("\n🎉 Collection creation complete!")


if __name__ == "__main__":
    main()
