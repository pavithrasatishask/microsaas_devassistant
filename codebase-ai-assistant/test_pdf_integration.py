#!/usr/bin/env python3
"""
Simple test script for PDF integration.
Run this after starting the Flask server.
"""
import requests
import json
import sys
from pathlib import Path

BASE_URL = "http://localhost:5000"

def print_response(title, response):
    """Pretty print API response."""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    try:
        data = response.json()
        print(json.dumps(data, indent=2))
        return data
    except:
        print(response.text)
        return None

def test_connect_repo_with_pdf(github_url, pdf_path, branch="main"):
    """Test connecting repository with PDF upload."""
    print(f"\n📦 Connecting repository: {github_url}")
    print(f"📄 Uploading PDF: {pdf_path}")
    
    if not Path(pdf_path).exists():
        print(f"❌ Error: PDF file not found: {pdf_path}")
        return None
    
    try:
        with open(pdf_path, 'rb') as f:
            files = {'pdf_files': (Path(pdf_path).name, f, 'application/pdf')}
            data = {
                'github_url': github_url,
                'branch': branch
            }
            response = requests.post(
                f"{BASE_URL}/api/repository/connect",
                files=files,
                data=data
            )
        
        result = print_response("Repository Connection Response", response)
        if result and result.get('success'):
            repo_id = result['data'].get('repo_id')
            print(f"\n✅ Repository connected! ID: {repo_id}")
            return repo_id
        else:
            print("\n❌ Failed to connect repository")
            return None
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return None

def test_get_documents(repo_id):
    """Test getting repository documents."""
    print(f"\n📋 Getting documents for repository {repo_id}...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/repository/{repo_id}/documents")
        result = print_response("Repository Documents", response)
        return result
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return None

def test_chat_with_pdf(repo_id, question):
    """Test chat with PDF context."""
    print(f"\n💬 Asking question with PDF context...")
    print(f"   Question: {question}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/chat/ask",
            json={
                'repo_id': repo_id,
                'question': question
            }
        )
        result = print_response("Chat Response", response)
        
        if result and result.get('success'):
            answer = result['data'].get('answer', '')
            print(f"\n✅ Answer received ({len(answer)} characters)")
            if 'pdf' in answer.lower() or 'document' in answer.lower():
                print("   ✓ PDF context appears to be included!")
        return result
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return None

def test_impact_analysis(repo_id, change_description):
    """Test impact analysis with PDF context."""
    print(f"\n🔍 Analyzing change impact with PDF context...")
    print(f"   Change: {change_description}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/analysis/analyze",
            json={
                'repo_id': repo_id,
                'change_description': change_description
            }
        )
        result = print_response("Impact Analysis Response", response)
        return result
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return None

def main():
    """Main test function."""
    print("🧪 PDF Integration Backend Test")
    print("="*60)
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code != 200:
            print("❌ Server is not responding. Make sure Flask server is running!")
            print("   Run: python app.py")
            sys.exit(1)
        print("✅ Server is running")
    except:
        print("❌ Cannot connect to server. Make sure Flask server is running!")
        print("   Run: python app.py")
        sys.exit(1)
    
    # Get inputs
    print("\n" + "="*60)
    print("Test Configuration")
    print("="*60)
    
    github_url = input("\nEnter GitHub repository URL: ").strip()
    if not github_url:
        print("❌ GitHub URL is required")
        sys.exit(1)
    
    pdf_path = input("Enter path to PDF file: ").strip()
    if not pdf_path:
        print("❌ PDF path is required")
        sys.exit(1)
    
    branch = input("Enter branch name (default: main): ").strip() or "main"
    
    # Run tests
    print("\n" + "="*60)
    print("Running Tests")
    print("="*60)
    
    # Test 1: Connect repository with PDF
    repo_id = test_connect_repo_with_pdf(github_url, pdf_path, branch)
    if not repo_id:
        print("\n❌ Test failed at repository connection")
        sys.exit(1)
    
    # Test 2: Get documents
    test_get_documents(repo_id)
    
    # Test 3: Chat with PDF context
    question = input("\nEnter a question to test PDF context (or press Enter for default): ").strip()
    if not question:
        question = "What are the main requirements or specifications in the document?"
    test_chat_with_pdf(repo_id, question)
    
    # Test 4: Impact analysis
    change = input("\nEnter a change description to test (or press Enter for default): ").strip()
    if not change:
        change = "Add new feature based on requirements"
    test_impact_analysis(repo_id, change)
    
    print("\n" + "="*60)
    print("✅ All tests completed!")
    print("="*60)
    print(f"\nRepository ID: {repo_id}")
    print(f"You can now test other endpoints using repo_id={repo_id}")

if __name__ == "__main__":
    main()

