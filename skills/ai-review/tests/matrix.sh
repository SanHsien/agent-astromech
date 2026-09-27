#!/bin/sh
# ai-review 行為驗收矩陣 —— 自己驗一次，別只信 README。
#
# 用法：
#   sh tests/matrix.sh                    # 驗旁邊那支 ../scripts/ai-review.sh
#   SH=bash sh tests/matrix.sh            # 指定「用哪個 shell 執行受測腳本」
#   AI_REVIEW_SH=/path/to/ai-review.sh sh tests/matrix.sh
#
# 特性：
# - **不燒任何額度**：後端一律用 stub 或 `cat` 模擬，不會真的呼叫 codex。
# - **不弄髒你的目錄**：所有產出寫在 mktemp 暫存區，跑完自動清掉。
# - 退出碼 0＝全過，1＝有失敗（可直接放進 CI）。
#
# MIT License — part of agent-astromech (github.com/SanHsien/agent-astromech maintained fork)

set -u

# 環境隔離：外層 shell 若 export 過這幾個變數（例如平常就把 AI_REVIEW_CMD 指到自己的後端），
# 會污染下面所有「乾淨環境」情境——實測過會造成 17 項假紅。測試自己要先把環境清乾淨。
unset AI_REVIEW_CMD AI_REVIEW_DIR AI_REVIEW_RUBRICS AI_REVIEW_TIMEOUT_SECONDS

DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || exit 1
S="${AI_REVIEW_SH:-$DIR/../scripts/ai-review.sh}"
SH="${SH:-/bin/sh}"
[ -f "$S" ] || { echo "❌ 找不到受測腳本：$S" >&2; exit 1; }

W=$(mktemp -d) || { echo "❌ 建不出暫存目錄" >&2; exit 1; }
trap 'rm -rf "$W"' EXIT
STUB="$W/stub"; mkdir -p "$STUB"
pass=0; fail=0; skip=0

printf 'def add(a,b):\n    return a-b   # bug\n' >"$W/sample.py"
printf 'second source\n' >"$W/s.txt"

chk() { # chk <label> <expect_status> <expect_rc> <actual_status> <actual_rc>
	if [ "$4" = "$2" ] && [ "$5" = "$3" ]; then
		printf '  ok   %-38s status=%-24s rc=%s\n' "$1" "$4" "$5"; pass=$((pass + 1))
	else
		printf '  FAIL %-38s got status=%s rc=%s (want %s / %s)\n' "$1" "$4" "$5" "$2" "$3"; fail=$((fail + 1))
	fi
}
ok_() { printf '  ok   %s\n' "$1"; pass=$((pass + 1)); }
no_() { printf '  FAIL %s\n' "$1"; fail=$((fail + 1)); }
skip_() { printf '  skip %s\n' "$1"; skip=$((skip + 1)); }

run() { # 執行並抓狀態行；stdout 被 $(…) 捕捉＝模擬真實呼叫端
	OUT=$("$@" 2>/dev/null); RC=$?
	ST=$(printf '%s' "$OUT" | sed -n 's/^AI_REVIEW_STATUS: //p' | tail -1)
}
mkstub() { # mkstub <exit_code> <stderr_text>：假裝成 codex
	cat >"$STUB/codex" <<EOF
#!/bin/sh
[ "\$1 \$2" = "login status" ] && { echo "Logged in"; exit 0; }
echo "$2" >&2
exit $1
EOF
	chmod +x "$STUB/codex"
}

echo "受測腳本：$S"
echo "執行 shell：$SH"
echo

echo "-- A. 後端錯誤分類（stub 模擬訊息，非真實後端輸出）--"
mkstub 1 "stream error: 429 Too Many Requests (rate limit exceeded)"
run env PATH="$STUB:/usr/bin:/bin" $SH "$S" "$W/sample.py" --rubric code
chk "額度(429)" failed_quota 2 "$ST" "$RC"
mkstub 1 "ERROR: not logged in. Please run codex login."
run env PATH="$STUB:/usr/bin:/bin" $SH "$S" "$W/sample.py" --rubric code
chk "未登入" skipped_not_logged_in 0 "$ST" "$RC"
mkstub 1 "error sending request: dns error: failed to lookup address"
run env PATH="$STUB:/usr/bin:/bin" $SH "$S" "$W/sample.py" --rubric code
chk "網路" failed_network 2 "$ST" "$RC"
mkstub 1 "403 Forbidden: this model is not available in your region"
run env PATH="$STUB:/usr/bin:/bin" $SH "$S" "$W/sample.py" --rubric code
chk "地區/政策" failed_policy 2 "$ST" "$RC"
mkstub 2 "error: unexpected argument '--ephemeral' found"
run env PATH="$STUB:/usr/bin:/bin" $SH "$S" "$W/sample.py" --rubric code
chk "版本不相容" failed_version 2 "$ST" "$RC"
mkstub 1 "something completely unfamiliar happened"
run env PATH="$STUB:/usr/bin:/bin" $SH "$S" "$W/sample.py" --rubric code
chk "無法歸類" failed_unknown 2 "$ST" "$RC"
cat >"$STUB/codex" <<'EOF'
#!/bin/sh
[ "$1 $2" = "login status" ] && { echo "Logged in"; exit 0; }
exit 0
EOF
chmod +x "$STUB/codex"
run env PATH="$STUB:/usr/bin:/bin" $SH "$S" "$W/sample.py" --rubric code
chk "空回覆" failed_empty 2 "$ST" "$RC"

echo "-- B. 沒有後端＝降級，不是錯誤 --"
run env PATH=/usr/bin:/bin $SH "$S" "$W/sample.py" --rubric code
chk "未安裝→exit 0" skipped_not_installed 0 "$ST" "$RC"
run env PATH=/usr/bin:/bin $SH "$S" "$W/sample.py" --rubric code --strict
chk "未安裝+--strict→exit 3" skipped_not_installed 3 "$ST" "$RC"
mkstub 1 "stream error: 429 rate limit exceeded"
run env PATH="$STUB:/usr/bin:/bin" $SH "$S" "$W/sample.py" --rubric code --soft-fail
chk "--soft-fail→failed 回 0" failed_quota 0 "$ST" "$RC"
run env PATH="$STUB:/usr/bin:/bin" $SH "$S" "$W/sample.py" --rubric code
chk "預設 failed 仍回 2" failed_quota 2 "$ST" "$RC"

echo "-- C. 可插拔後端 AI_REVIEW_CMD --"
run env PATH=/usr/bin:/bin AI_REVIEW_CMD='sed -n "1,3p"' $SH "$S" "$W/sample.py" --rubric code --no-save
chk "自訂後端可用" ok 0 "$ST" "$RC"
run env PATH=/usr/bin:/bin AI_REVIEW_CMD='definitely_not_a_real_command_xyz' $SH "$S" "$W/sample.py" --rubric code
chk "自訂後端不存在→skipped" skipped_not_installed 0 "$ST" "$RC"
run env PATH=/usr/bin:/bin AI_REVIEW_CMD='sh -c "echo not logged in >&2; exit 1"' $SH "$S" "$W/sample.py" --rubric code
chk "自訂後端未登入→skipped" skipped_not_logged_in 0 "$ST" "$RC"
run env PATH=/usr/bin:/bin AI_REVIEW_CMD='false' $SH "$S" "$W/sample.py" --rubric code
chk "自訂後端失敗→failed" failed_unknown 2 "$ST" "$RC"
run env PATH=/usr/bin:/bin AI_REVIEW_CMD='sleep 5; printf should_not_finish' $SH "$S" "$W/sample.py" --rubric code --timeout 1
chk "自訂後端逾時→failed_timeout" failed_timeout 2 "$ST" "$RC"
cat >"$STUB/codex" <<'EOF'
#!/bin/sh
[ "$1 $2" = "login status" ] && { sleep 5; echo "Logged in"; exit 0; }
exit 0
EOF
chmod +x "$STUB/codex"
run env PATH="$STUB:/usr/bin:/bin" $SH "$S" "$W/sample.py" --rubric code --timeout 1
chk "Codex 登入檢查逾時" failed_timeout 2 "$ST" "$RC"
cat >"$STUB/codex" <<'EOF'
#!/bin/sh
[ "$1 $2" = "login status" ] && { echo "Logged in"; exit 0; }
sleep 5
EOF
chmod +x "$STUB/codex"
run env PATH="$STUB:/usr/bin:/bin" $SH "$S" "$W/sample.py" --rubric code --timeout 1
chk "Codex review 呼叫逾時" failed_timeout 2 "$ST" "$RC"

echo "-- D. 呼叫鏈：降級不得中斷上層 --"
cat >"$W/chain.sh" <<EOF
#!/bin/sh
set -e
R=\$(env PATH=/usr/bin:/bin $SH "$S" "$W/sample.py" --rubric code 2>/dev/null)
echo UPSTREAM_ALIVE
printf '%s' "\$R" | sed -n 's/^AI_REVIEW_STATUS: //p'
EOF
chmod +x "$W/chain.sh"
CHAIN=$("$W/chain.sh" 2>&1); CRC=$?
if [ "$CRC" -eq 0 ] && printf '%s' "$CHAIN" | grep -q UPSTREAM_ALIVE; then
	ok_ "set -e + \$(…) 下上層存活"
else
	no_ "set -e + \$(…) 下上層存活（rc=$CRC）"
fi
# 負對照組：真失敗（429、未帶 --soft-fail）必須讓 set -e 的上層確實中斷——
# 與上面的正面案例成對，證明「該停的時候真的會停」，不是腳本永遠回 0。
mkstub 1 "stream error: 429 Too Many Requests (rate limit exceeded)"
cat >"$W/chain2.sh" <<EOF
#!/bin/sh
set -e
R=\$(env PATH="$STUB:/usr/bin:/bin" $SH "$S" "$W/sample.py" --rubric code 2>/dev/null)
echo SHOULD_NOT_REACH
EOF
chmod +x "$W/chain2.sh"
CHAIN2=$("$W/chain2.sh" 2>&1); CRC2=$?
if [ "$CRC2" -ne 0 ] && ! printf '%s' "$CHAIN2" | grep -q SHOULD_NOT_REACH; then
	ok_ "負對照：真失敗在 set -e 下確實中斷上層"
else
	no_ "負對照：真失敗沒有中斷上層（rc=$CRC2）"
fi

echo "-- E. 環境邊界 --"
SP="$W/dir with space"; mkdir -p "$SP/scripts" "$SP/rubrics"
cp "$S" "$SP/scripts/ai-review.sh"
cp "$DIR/../rubrics/"*.md "$SP/rubrics/" 2>/dev/null
cp "$W/sample.py" "$SP/my sample.py"
run env PATH=/usr/bin:/bin $SH "$SP/scripts/ai-review.sh" "$SP/my sample.py" --rubric code
chk "路徑含空白" skipped_not_installed 0 "$ST" "$RC"
RO="$W/ro"; mkdir -p "$RO"; chmod 500 "$RO"
run env PATH=/usr/bin:/bin AI_REVIEW_DIR="$RO/nested" AI_REVIEW_CMD='cat' $SH "$S" "$W/sample.py" --rubric code
chk "落檔目錄不可寫仍 ok" ok 0 "$ST" "$RC"
chmod 700 "$RO"
ST=$(printf 'hello\n' | env PATH=/usr/bin:/bin AI_REVIEW_CMD='cat' $SH "$S" - --rubric copy --no-save 2>/dev/null | sed -n 's/^AI_REVIEW_STATUS: //p'); RC=$?
chk "stdin 來源" ok 0 "$ST" "$RC"
# 傳給後端的路徑格式（Windows 迴歸）。上面每一項的 stub 都是 sh 腳本，POSIX 路徑照吃，
# 所以整份矩陣看不見「真實 codex 是原生 Windows exe、看不懂 /tmp/xxx」這個缺陷
# （實錯：-C 收到 POSIX 路徑 → `os error 2` → 被歸成 failed_unknown）。
# 這一項改成攔截 argv：不看後端做了什麼，只看它收到的 -C／-o 長什麼樣。
cat >"$STUB/codex" <<'EOF'
#!/bin/sh
[ "$1 $2" = "login status" ] && { echo "Logged in"; exit 0; }
for a in "$@"; do printf '%s\n' "$a"; done >"$ARGV_OUT"
exit 1
EOF
chmod +x "$STUB/codex"
ARGV="$W/argv.txt"
env PATH="$STUB:/usr/bin:/bin" ARGV_OUT="$ARGV" $SH "$S" "$W/sample.py" --rubric code >/dev/null 2>&1
CDIR=$(grep -A1 -x -e '-C' "$ARGV" 2>/dev/null | tail -1)
case "$(uname -s 2>/dev/null || printf unknown)" in
MINGW* | MSYS* | CYGWIN*)
	case "$CDIR" in
	/*) no_ "傳給後端的 -C 已轉成 Windows 路徑（實得 POSIX：$CDIR）" ;;
	?:\\*) ok_ "傳給後端的 -C 已轉成 Windows 路徑" ;;
	*) no_ "傳給後端的 -C 形式無法辨識（實得：$CDIR）" ;;
	esac
	;;
*)
	case "$CDIR" in
	/*) ok_ "傳給後端的 -C 在 POSIX 平台維持 POSIX 路徑" ;;
	*) no_ "傳給後端的 -C 在 POSIX 平台被動到了（實得：$CDIR）" ;;
	esac
	;;
esac

echo "-- F. 用法錯誤（全部 exit 1，不印狀態）--"
run env PATH=/usr/bin:/bin $SH "$S" "$W/sample.py"
chk "缺 --rubric" "" 1 "$ST" "$RC"
run env PATH=/usr/bin:/bin $SH "$S" "$W/nope.py" --rubric code
chk "來源不存在" "" 1 "$ST" "$RC"
run env PATH=/usr/bin:/bin $SH "$S" "$W/sample.py" --rubric /nonexistent/r.md
chk "rubric 不存在" "" 1 "$ST" "$RC"
run env PATH=/usr/bin:/bin $SH "$S" "$W/sample.py" --rubric code --effort banana
chk "--effort 非法值" "" 1 "$ST" "$RC"
run env PATH=/usr/bin:/bin $SH "$S" "$W/sample.py" "$W/s.txt" --rubric code
chk "一次給兩份來源" "" 1 "$ST" "$RC"
run env PATH=/usr/bin:/bin $SH "$S" "$W/sample.py" --rubric code --strict --soft-fail
chk "兩開關併用" "" 1 "$ST" "$RC"
run env PATH=/usr/bin:/bin AI_REVIEW_TIMEOUT_SECONDS=0 $SH "$S" "$W/sample.py" --rubric code
chk "timeout 非正整數" "" 1 "$ST" "$RC"
run env PATH=/usr/bin:/bin AI_REVIEW_CMD='cat' $SH "$S" --rubric code --no-save -- "$W/sample.py"
chk "-- 之後當來源檔" ok 0 "$ST" "$RC"

echo "-- G. 分類器不得把真失敗吞成 skipped（安靜的假成功）--"
mkstub 1 "authorization policy denied for this organization"
run env PATH="$STUB:/usr/bin:/bin" $SH "$S" "$W/sample.py" --rubric code
chk "policy 不判成未登入" failed_policy 2 "$ST" "$RC"
mkstub 1 "auth service unavailable, connection reset"
run env PATH="$STUB:/usr/bin:/bin" $SH "$S" "$W/sample.py" --rubric code
chk "auth 字樣實為網路" failed_network 2 "$ST" "$RC"
mkstub 1 "internal server error; request 401abc failed, retry in 401 seconds"
run env PATH="$STUB:/usr/bin:/bin" $SH "$S" "$W/sample.py" --rubric code
chk "401 數字不判成未登入" failed_unknown 2 "$ST" "$RC"
mkstub 1 "HTTP 401 Unauthorized: please sign in"
run env PATH="$STUB:/usr/bin:/bin" $SH "$S" "$W/sample.py" --rubric code
chk "帶語境 401→未登入" skipped_not_logged_in 0 "$ST" "$RC"
cat >"$STUB/codex" <<'EOF'
#!/bin/sh
[ "$1 $2" = "login status" ] && { echo "Logged in using ChatGPT (sign-in method: browser; session expires in 401 seconds)"; exit 0; }
echo "backend reached" >&2; exit 1
EOF
chmod +x "$STUB/codex"
run env PATH="$STUB:/usr/bin:/bin" $SH "$S" "$W/sample.py" --rubric code
chk "已登入訊息不被誤判" failed_unknown 2 "$ST" "$RC"

echo "-- H. 落檔：不覆蓋、不外洩、不被 symlink 騙 --"
COLL="$W/collide"
env PATH=/usr/bin:/bin AI_REVIEW_DIR="$COLL" AI_REVIEW_CMD='cat' $SH "$S" "$W/sample.py" --rubric code >/dev/null 2>&1
env PATH=/usr/bin:/bin AI_REVIEW_DIR="$COLL" AI_REVIEW_CMD='cat' $SH "$S" "$W/sample.py" --rubric code >/dev/null 2>&1
N=$(ls "$COLL" 2>/dev/null | wc -l | tr -d ' ')
[ "$N" = "2" ] && ok_ "同秒兩次不互相覆蓋" || no_ "同秒兩次不互相覆蓋（只剩 $N 份）"
PERM=$(ls -l "$COLL"/*.md 2>/dev/null | head -1 | cut -c1-10)
if [ "$PERM" = "-rw-------" ]; then
	ok_ "落檔權限 600"
else
	case "$(uname -s 2>/dev/null || printf unknown)" in
		MINGW*|MSYS*) skip_ "落檔權限 600（NTFS/Git Bash 不提供 POSIX mode-bit 證據；Linux CI 必驗）" ;;
		*) no_ "落檔權限 600（實際 $PERM）" ;;
	esac
fi
LEFT=$(ls -a "$COLL" 2>/dev/null | grep '^\.ai-review\.' | wc -l | tr -d ' ')
[ "$LEFT" = "0" ] && ok_ "不留暫存殘檔" || no_ "不留暫存殘檔（$LEFT 個）"
VIC="$W/victim.txt"; printf 'DO_NOT_TOUCH\n' >"$VIC"
SD="$W/symdir"; mkdir -p "$SD"; ln -s "$VIC" "$SD/.ai-review.$$.tmp" 2>/dev/null
env PATH=/usr/bin:/bin AI_REVIEW_DIR="$SD" AI_REVIEW_CMD='cat' $SH "$S" "$W/sample.py" --rubric code >/dev/null 2>&1
[ "$(cat "$VIC")" = "DO_NOT_TOUCH" ] && ok_ "暫存檔 symlink 攻擊不生效" || no_ "暫存檔 symlink 攻擊寫穿了受害檔"
RD="$W/rub"; mkdir -p "$RD"; printf 'custom rubric\n' >"$RD/my.md"
GD="$W/gout"
env PATH=/usr/bin:/bin AI_REVIEW_DIR="$GD" AI_REVIEW_CMD='cat' $SH "$S" "$W/sample.py" --rubric "$RD/my.md" >/dev/null 2>&1
if [ "$(ls "$GD" 2>/dev/null | wc -l | tr -d ' ')" = "1" ] && ls "$GD" | grep -q -- "-custom-"; then
	ok_ "自訂 rubric 路徑不進檔名"
else
	no_ "自訂 rubric 路徑不進檔名"
fi
ODD="$W/odd: name .md"; cp "$W/sample.py" "$ODD"
YD="$W/yaml"
env PATH=/usr/bin:/bin AI_REVIEW_DIR="$YD" AI_REVIEW_CMD='cat' $SH "$S" "$ODD" --rubric code >/dev/null 2>&1
YF=$(ls "$YD"/*.md 2>/dev/null | head -1)
if [ -z "$YF" ]; then
	no_ "特殊檔名仍落得了檔"
elif command -v python3 >/dev/null 2>&1 && python3 -c "import yaml" >/dev/null 2>&1; then
	# 兩個 Windows 坑，兩個都會讓一份**其實合法**的 frontmatter 被誤判成壞掉：
	# ① 路徑：Git Bash 上的 python3 常是原生 Windows 直譯器（如 Windows Store 版），
	#    讀不懂 `/tmp/xxx`，開檔直接 FileNotFoundError → 改用 stdin 餵內容。
	# ② 編碼：Windows 的 `sys.stdin.read()` 依 locale 預設編碼解碼（cp950…），
	#    會把 UTF-8 中文解成代理字元，PyYAML 報 `unacceptable character #xdce5`
	#    → 改讀 `stdin.buffer` 自己指定 utf-8，不看環境臉色。
	# 🔴 別退回 `sys.stdin.read()`：它在有設 PYTHONIOENCODING 的 shell 會過、
	#    沒設的會紅，是那種「跑起來時好時壞、看起來像 flaky」的假訊號（姊妹 skill 實錯）。
	if python3 -c "
import sys,yaml,re
s=sys.stdin.buffer.read().decode('utf-8')
m=re.match(r'^---\n(.*?)\n---\n',s,re.S)
yaml.safe_load(m.group(1))
" <"$YF" >/dev/null 2>&1; then
		ok_ "特殊檔名的 frontmatter 仍是合法 YAML"
	else
		no_ "特殊檔名的 frontmatter 壞了"
	fi
else
	skip_ "frontmatter YAML 驗證（本機無 python3+pyyaml）"
fi
CN="$W/這是一個很長的中文檔名用來測試截斷行為超過六十個字元的情況繼續加長繼續加長繼續加長.md"
cp "$W/sample.py" "$CN"
LD="$W/locale"
env LC_ALL=C PATH=/usr/bin:/bin AI_REVIEW_DIR="$LD" AI_REVIEW_CMD='cat' $SH "$S" "$CN" --rubric code >/dev/null 2>&1
[ "$(ls "$LD" 2>/dev/null | wc -l | tr -d ' ')" = "1" ] && ok_ "非 UTF-8 locale 下長中文檔名仍落檔" || no_ "非 UTF-8 locale 下長中文檔名落檔失敗"

echo "-- I. 失敗時看得到原因 --"
OUT2=$(env PATH=/usr/bin:/bin AI_REVIEW_CMD='sh -c "echo hidden_reason >&2; exit 0"' $SH "$S" "$W/sample.py" --rubric code 2>&1 >/dev/null)
printf '%s' "$OUT2" | grep -q hidden_reason && ok_ "空回覆會印出後端 stderr" || no_ "空回覆沒印出後端 stderr"
OUT3=$(env PATH=/usr/bin:/bin AI_REVIEW_CMD='sh -c "echo stdout_only_error; exit 1"' $SH "$S" "$W/sample.py" --rubric code 2>&1 >/dev/null)
printf '%s' "$OUT3" | grep -q stdout_only_error && ok_ "錯誤寫在 stdout 也照印" || no_ "錯誤寫在 stdout 沒印出來"

printf '\n總計：%s 過 / %s 失敗' "$pass" "$fail"
[ "$skip" -gt 0 ] && printf ' / %s 略過' "$skip"
printf '\n'
[ "$fail" -eq 0 ]
