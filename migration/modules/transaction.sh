#!/usr/bin/env bash
set -u
set -o pipefail

TX_ROOT=""
TX_JOURNAL=""

tx_configure() {
  TX_ROOT="$1"
  mkdir -p "$TX_ROOT/transactions"
  TX_JOURNAL="$TX_ROOT/transactions/journal.jsonl"
}

tx_new_id() {
  local seq=1
  local sequence_file="$TX_ROOT/transactions/sequence"
  if [[ -f "$sequence_file" ]]; then
    seq=$(( $(cat "$sequence_file") + 1 ))
  fi
  printf '%s\n' "$seq" > "$sequence_file"
  printf 'TX-%06d' "$seq"
}

tx_append() {
  local tx_id="$1" event="$2" result="${3:-pending}"
  python3 - "$TX_JOURNAL" "$tx_id" "$event" "$result" <<'PY'
import json,sys
from datetime import datetime,timezone
path,tx,event,result=sys.argv[1:]
record={"schema_version":1,"transaction_id":tx,"event":event,"result":result,"timestamp":datetime.now(timezone.utc).isoformat().replace("+00:00","Z")}
with open(path,"a",encoding="utf-8") as handle:
    handle.write(json.dumps(record,sort_keys=True,separators=(",",":"))+"\n")
PY
}

tx_begin() {
  local operation="$1" parent_state="$2"
  local tx_id
  tx_id="$(tx_new_id)"
  tx_append "$tx_id" "begin:$operation" "pending"
  tx_append "$tx_id" "parent_state:$parent_state" "recorded"
  printf '%s\n' "$tx_id"
}

tx_record_precondition() {
  tx_append "$1" "precondition:$2=$3" "recorded"
}

tx_record_action() {
  tx_append "$1" "action:$2" "planned"
}

tx_record_result() {
  tx_append "$1" "result" "$2"
}

tx_commit() {
  tx_append "$1" "commit" "committed"
}

tx_abort() {
  tx_append "$1" "abort:$2" "aborted"
}
