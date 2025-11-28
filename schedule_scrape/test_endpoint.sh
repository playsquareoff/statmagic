#!/bin/bash
# Test script for the schedule_scrape Lambda API endpoint

ENDPOINT="https://lf7a6w0f7g.execute-api.us-west-2.amazonaws.com/schedule"

echo "=========================================="
echo "Testing Schedule Scrape Lambda Endpoint"
echo "=========================================="
echo ""

# Test 1: Default (Minnesota Vikings)
echo "1. Testing default (Minnesota Vikings):"
echo "   GET $ENDPOINT"
curl -s "$ENDPOINT" | python3 -m json.tool | head -20
echo ""
echo ""

# Test 2: Dallas Cowboys
echo "2. Testing Dallas Cowboys:"
echo "   GET $ENDPOINT?team_slug=dal&team_name_long=dallas-cowboys"
curl -s "$ENDPOINT?team_slug=dal&team_name_long=dallas-cowboys" | python3 -m json.tool | head -20
echo ""
echo ""

# Test 3: Seattle Seahawks
echo "3. Testing Seattle Seahawks:"
echo "   GET $ENDPOINT?team_slug=sea&team_name_long=seattle-seahawks"
curl -s "$ENDPOINT?team_slug=sea&team_name_long=seattle-seahawks" | python3 -m json.tool | head -20
echo ""
echo ""

# Test 4: POST with JSON body
echo "4. Testing POST with JSON body (Green Bay Packers):"
echo "   POST $ENDPOINT"
curl -s -X POST "$ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{"team_slug":"gb","team_name_long":"green-bay-packers"}' | python3 -m json.tool | head -20
echo ""
echo ""

# Test 5: Error handling
echo "5. Testing error handling (invalid team):"
echo "   GET $ENDPOINT?team_slug=invalid&team_name_long=invalid-team"
curl -s "$ENDPOINT?team_slug=invalid&team_name_long=invalid-team" | python3 -m json.tool
echo ""
echo ""

echo "=========================================="
echo "All tests completed!"
echo "=========================================="

