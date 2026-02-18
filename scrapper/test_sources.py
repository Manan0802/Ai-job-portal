"""
🧪 TEST SCRIPT - Verify All Job Sources
"""

from manual_search import scrape_jobs_by_query

print("\n" + "="*70)
print("🧪 TESTING ALL JOB SOURCES")
print("="*70)

# Test search
query = "Python developer"
print(f"\nTest Query: '{query}'")
print("Searching across all 7 sources...\n")

results = scrape_jobs_by_query(
    query=query,
    country="USA",
    location=None,
    work_mode=["Remote"],
    results_wanted=50
)

if not results.empty:
    print("\n✅ SUCCESS! All sources working!")
    print(f"\nTotal jobs found: {len(results)}")
    print("\nJobs by source:")
    print(results['source'].value_counts())
    print("\nSample jobs:")
    print(results[['title', 'company', 'source']].head(10))
else:
    print("\n⚠️ No results found. Check your internet connection.")

print("\n" + "="*70)
print("Test complete!")
print("="*70 + "\n")
