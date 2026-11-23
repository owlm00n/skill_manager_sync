#!/usr/bin/env python3
"""
RAGFlow Semantic Retrieval Script for PD认证 Analysis
======================================================
Unified search client — all queries route to PD认证 KB via explicit knowledge_id.
Authorization: Bearer <api_key>

Usage:
  python ragflow_search.py "<query>" --phase 2 --top-k 5
  python ragflow_search.py --batch queries.json --output-dir results/
  python ragflow_search.py --health
"""

import urllib.request
import urllib.error
import json
import sys
import os
import time
import argparse
import io

# Fix Windows GBK encoding issues with Unicode characters
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ============================================================
# CONFIGURATION
# ============================================================
API_KEY = "ragflow-TChpP9Qz85dW-WF492VdAAp_7HZxuTKI6L4P8yBekpY"
BASE_URL = "http://10.30.12.54:81/api/v1"
PD_AUTH_KB_ID = "ca6740b297af11f19f9e7d0056ecab0b"  # PD认证 KB (primary target)

# ============================================================
# CORE FUNCTIONS
# ============================================================

def ragflow_retrieve(query, knowledge_id=PD_AUTH_KB_ID, top_k=5, score_threshold=0.2, use_kg=False):
    """
    Execute a single RAGFlow retrieval query against a specific knowledge base.

    Args:
        query (str): Search query string
        knowledge_id (str): Target KB ID (default: PD认证)
        top_k (int): Number of results to return
        score_threshold (float): Minimum similarity score threshold
        use_kg (bool): Whether to use knowledge graph enhancement

    Returns:
        list[dict]: Retrieved chunks with score, title, content, source fields
    """
    payload = json.dumps({
        "knowledge_id": knowledge_id,
        "query": query,
        "use_kg": use_kg,
        "retrieval_setting": {
            "top_k": top_k,
            "score_threshold": score_threshold
        }
    }).encode('utf-8')

    url = f"{BASE_URL}/dify/retrieval"
    req = urllib.request.Request(url, data=payload)
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {API_KEY}")

    try:
        resp = urllib.request.urlopen(req, timeout=30)
        result = json.loads(resp.read().decode())
        if isinstance(result, list):
            return result
        elif isinstance(result, dict) and "chunks" in result:
            return result["chunks"]
        elif isinstance(result, dict) and "data" in result:
            return result["data"]
        else:
            return [result] if result else []
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return [{"error": f"HTTP {e.code}", "body": body[:500]}]
    except Exception as e:
        return [{"error": str(e)}]


def health_check():
    """Verify RAGFlow API connectivity and list all available knowledge bases."""
    print("=" * 60)
    print("RAGFlow Health Check")
    print("=" * 60)

    # Test 1: List datasets
    print("\n[1/3] Listing datasets...")
    try:
        url = f"{BASE_URL}/datasets"
        req = urllib.request.Request(url)
        req.add_header("Authorization", f"Bearer {API_KEY}")
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read().decode())
        if isinstance(data, list):
            print(f"  [OK] {len(data)} datasets found")
            for ds in data:
                kb_id = ds.get('id', '?')[:12]
                name = ds.get('name', '?')
                files = ds.get('doc_num', '?')
                status = ds.get('status', '?')
                print(f"     [{kb_id}...] {name} (files: {files}, status: {status})")
        elif isinstance(data, dict) and "data" in data:
            items = data["data"]
            print(f"  [OK] {len(items)} datasets found")
            for ds in items[:20]:
                print(f"     [{ds.get('id','?')[:12]}...] {ds.get('name','?')}")
    except Exception as e:
        print(f"  [FAIL] {e}")

    # Test 2: Verify PD认证 KB
    print(f"\n[2/3] Testing PD认证 KB ({PD_AUTH_KB_ID[:12]}...)...")
    results = ragflow_retrieve("TEST.PD.PROT.SNK.12 测试步骤", top_k=3)
    if results and not results[0].get("error"):
        print(f"  [OK] Returns {len(results)} chunks")
        for r in results[:3]:
            print(f"     [{r.get('score', 'N/A')}] {r.get('title', 'N/A')[:80]}")
    else:
        print(f"  [FAIL] {results[0].get('error') if results else 'empty'}")

    # Test 3: Confirm auth method
    print("\n[3/3] Auth method: Bearer <api_key> [OK]")
    print("\nHealth check complete.")


def run_batch_queries(queries_file, output_dir=None):
    """
    Execute all queries defined in a JSON batch file.

    Expected JSON format:
    {
        "case_id": "3523391",
        "case_name": "TEST.PD.PROT.SNK.12",
        "date": "2026-09-17",
        "knowledge_base": "PD认证",
        "knowledge_id": "ca6740b297af11f19f9e7d0056ecab0b",
        "auth_method": "Bearer",
        "phases": {
            "2": {
                "search_logic": "CTS test flow lookup — ...",
                "queries": ["query1", "query2", ...]
            },
            ...
        }
    }

    Args:
        queries_file (str): Path to JSON query definition file
        output_dir (str): Directory for raw result JSON files (default: same dir as queries_file)
    """
    with open(queries_file, 'r', encoding='utf-8') as f:
        batch = json.load(f)

    if output_dir is None:
        output_dir = os.path.dirname(os.path.abspath(queries_file))

    os.makedirs(output_dir, exist_ok=True)

    phases = batch.get("phases", {})
    total_queries = sum(len(p.get("queries", [])) for p in phases.values())
    case_id = batch.get("case_id", "unknown")
    print(f"Running {total_queries} queries across {len(phases)} phases for Case {case_id}...")
    print(f"Target KB: {batch.get('knowledge_base', 'PD认证')} ({batch.get('knowledge_id', PD_AUTH_KB_ID)[:12]}...)")
    print(f"Output: {output_dir}")

    all_results = {}

    for phase_num in sorted(phases.keys(), key=int):
        phase_data = phases[phase_num]
        phase_queries = phase_data.get("queries", [])
        search_logic = phase_data.get("search_logic", "")

        print(f"\n{'='*60}")
        print(f"Phase {phase_num}: {len(phase_queries)} queries")
        print(f"Search logic: {search_logic[:120]}")
        print(f"{'='*60}")

        phase_results = []
        for i, query in enumerate(phase_queries):
            print(f"\n  [{i+1}/{len(phase_queries)}] {query[:100]}...")
            results = ragflow_retrieve(query, knowledge_id=batch.get("knowledge_id", PD_AUTH_KB_ID))
            if results and not results[0].get("error"):
                chunk_count = len(results)
                top_score = 0
                if results and isinstance(results, list) and len(results) > 0:
                    records = results[0].get('records', []) if isinstance(results[0], dict) else []
                    if records and len(records) > 0:
                        top_score = records[0].get('score', 0)
                print(f"    → {chunk_count} chunks, top_score={top_score}")
                result_entry = {
                    "query": query,
                    "query_index": i,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "total_chunks": chunk_count,
                    "top_score": top_score,
                    "chunks": results
                }
            else:
                error_msg = results[0].get('error', 'empty') if results else 'empty'
                print(f"    → ERROR: {error_msg}")
                result_entry = {
                    "query": query,
                    "query_index": i,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "total_chunks": 0,
                    "error": error_msg,
                    "chunks": []
                }
            phase_results.append(result_entry)

            # Small delay between queries to avoid overwhelming the server
            time.sleep(0.5)

        # Save per-phase raw results
        output_path = os.path.join(output_dir, f"01_RAW_RESULTS_PHASE_{phase_num}.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                "case_id": case_id,
                "phase": phase_num,
                "search_logic": search_logic,
                "knowledge_id": batch.get("knowledge_id", PD_AUTH_KB_ID),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "total_queries": len(phase_queries),
                "results": phase_results
            }, f, ensure_ascii=False, indent=2)
        print(f"\n  [OK] Phase {phase_num} results saved: {output_path}")

        all_results[phase_num] = phase_results

    # Save consolidated manifest
    manifest = {
        "case_id": case_id,
        "case_name": batch.get("case_name", ""),
        "date": batch.get("date", ""),
        "knowledge_base": batch.get("knowledge_base", "PD认证"),
        "knowledge_id": batch.get("knowledge_id", PD_AUTH_KB_ID),
        "auth_method": "Bearer",
        "total_queries": total_queries,
        "phases_executed": list(phases.keys()),
        "phase_summary": {}
    }
    for phase_num, results in all_results.items():
        total = len(results)
        success = sum(1 for r in results if r.get("total_chunks", 0) > 0)
        manifest["phase_summary"][phase_num] = {
            "queries": total,
            "successful": success,
            "failed": total - success
        }

    manifest_path = os.path.join(output_dir, "manifest.json")
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"BATCH COMPLETE")
    print(f"  Total queries: {total_queries}")
    for phase_num, summary in manifest["phase_summary"].items():
        print(f"  Phase {phase_num}: {summary['successful']}/{summary['queries']} successful")
    print(f"  Manifest: {manifest_path}")
    print(f"{'='*60}")

    return all_results


# ============================================================
# CLI ENTRY POINT
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="RAGFlow Semantic Retrieval for PD认证 Analysis"
    )
    parser.add_argument("query", nargs="?", help="Single search query")
    parser.add_argument("--phase", "-p", type=str, help="Phase number (for logging)")
    parser.add_argument("--top-k", "-k", type=int, default=5, help="Number of results (default: 5)")
    parser.add_argument("--threshold", "-t", type=float, default=0.2, help="Score threshold (default: 0.2)")
    parser.add_argument("--batch", "-b", type=str, help="Path to batch query JSON file")
    parser.add_argument("--output-dir", "-o", type=str, help="Output directory for batch results")
    parser.add_argument("--health", action="store_true", help="Run health check")
    parser.add_argument("--json", action="store_true", help="Output results as raw JSON")

    args = parser.parse_args()

    if args.health:
        health_check()
        return

    if args.batch:
        run_batch_queries(args.batch, args.output_dir)
        return

    if args.query:
        results = ragflow_retrieve(args.query, top_k=args.top_k, score_threshold=args.threshold)

        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            print(f"\nQuery: {args.query}")
            print(f"Phase: {args.phase or 'N/A'}")
            print(f"Results: {len(results) if results and not results[0].get('error') else 'ERROR'}")
            print("-" * 60)
            for i, r in enumerate(results):
                if r.get("error"):
                    print(f"  [{i}] ERROR: {r['error']}")
                else:
                    score = r.get('score', 'N/A')
                    title = r.get('title', 'N/A')
                    content_preview = r.get('content', '')[:150]
                    print(f"  [{i}] score={score} | {title}")
                    print(f"      {content_preview}...")
        return

    parser.print_help()


if __name__ == "__main__":
    main()