#!/bin/bash

echo "========================================="
echo "Complete Authentication System Test"
echo "========================================="
echo ""

# Test 1: Register new user
echo "1. Register new user"
echo "-------------------"
EMAIL="test_$(date +%s)@example.com"
PASSWORD="TestPassword123!"
echo "Email: $EMAIL"
echo "Password: $PASSWORD"

REGISTER_RESPONSE=$(curl -s -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")

echo "$REGISTER_RESPONSE" | jq .
TOKEN=$(echo "$REGISTER_RESPONSE" | jq -r '.access_token')
USER_ID=$(echo "$REGISTER_RESPONSE" | jq -r '.user_id')

if [ "$TOKEN" != "null" ] && [ -n "$TOKEN" ]; then
  echo "✅ Registration successful"
  echo "User ID: $USER_ID"
  echo "Token: ${TOKEN:0:50}..."
else
  echo "❌ Registration failed"
  exit 1
fi

# Test 2: Sign in with same credentials
echo ""
echo "2. Sign in with existing credentials"
echo "------------------------------------"
SIGNIN_RESPONSE=$(curl -s -X POST "http://localhost:8000/auth/token" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")

echo "$SIGNIN_RESPONSE" | jq .
TOKEN=$(echo "$SIGNIN_RESPONSE" | jq -r '.access_token')

if [ "$TOKEN" != "null" ] && [ -n "$TOKEN" ]; then
  echo "✅ Sign in successful"
else
  echo "❌ Sign in failed"
  exit 1
fi

# Test 3: Wrong credentials
echo ""
echo "3. Test wrong credentials (should fail)"
echo "----------------------------------------"
WRONG_RESPONSE=$(curl -s -X POST "http://localhost:8000/auth/token" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"WrongPassword\"}")

if echo "$WRONG_RESPONSE" | jq -e '.access_token' > /dev/null 2>&1; then
  echo "❌ Should have failed with wrong password!"
  exit 1
else
  echo "✅ Correctly rejected wrong credentials"
fi

# Test 4: Create note with Bearer token
echo ""
echo "4. Create note with Bearer token"
echo "---------------------------------"
NOTE_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/notes" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Auth Test Note","tags":"test,swagger","text_notes":"Created with Bearer token from Swagger auth"}')

echo "$NOTE_RESPONSE" | jq .
NOTE_ID=$(echo "$NOTE_RESPONSE" | jq -r '.id')

if [ "$NOTE_ID" != "null" ] && [ -n "$NOTE_ID" ]; then
  echo "✅ Note created successfully (ID: $NOTE_ID)"
else
  echo "❌ Failed to create note"
  exit 1
fi

# Test 5: Get note
echo ""
echo "5. Get note with Bearer token"
echo "------------------------------"
GET_RESPONSE=$(curl -s -X GET "http://localhost:8000/api/notes/$NOTE_ID" \
  -H "Authorization: Bearer $TOKEN")

echo "$GET_RESPONSE" | jq .
if echo "$GET_RESPONSE" | jq -e '.id' > /dev/null 2>&1; then
  echo "✅ Note retrieved successfully"
else
  echo "❌ Failed to get note"
  exit 1
fi

# Test 6: Try without token (should fail)
echo ""
echo "6. Try to create note without token (should fail)"
echo "--------------------------------------------------"
NO_AUTH_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/notes" \
  -H "Content-Type: application/json" \
  -d '{"title":"Should Fail","tags":"test","text_notes":"No auth"}')

if echo "$NO_AUTH_RESPONSE" | jq -e '.id' > /dev/null 2>&1; then
  echo "❌ Should have failed without token!"
  exit 1
else
  echo "✅ Correctly rejected request without authentication"
fi

# Test 7: Delete note
echo ""
echo "7. Delete note with Bearer token"
echo "--------------------------------"
DELETE_RESPONSE=$(curl -s -X DELETE "http://localhost:8000/api/notes/$NOTE_ID" \
  -H "Authorization: Bearer $TOKEN")

echo "$DELETE_RESPONSE" | jq .
if echo "$DELETE_RESPONSE" | jq -e '.message' > /dev/null 2>&1; then
  echo "✅ Note deleted successfully"
else
  echo "❌ Failed to delete note"
  exit 1
fi

# Summary
echo ""
echo "========================================="
echo "✅ All authentication tests passed!"
echo "========================================="
echo ""
echo "Summary:"
echo "- Registration endpoint: /auth/register"
echo "- Sign in endpoint: /auth/token"
echo "- Bearer token authentication: Working"
echo "- Unauthorized access protection: Working"
echo ""
echo "How to use in Swagger UI:"
echo "1. Go to http://localhost:8000/docs"
echo "2. Call /auth/register or /auth/token endpoint"
echo "3. Copy the access_token from the response"
echo "4. Click the 'Authorize' button (lock icon) at the top"
echo "5. Paste the token (Swagger will add 'Bearer' prefix automatically)"
echo "6. Click 'Authorize' then 'Close'"
echo "7. Now you can call any protected endpoint"
echo ""
