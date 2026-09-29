#!/bin/zsh
# One-time setup (needs admin): a low-privilege macOS user `cmsim` that runs simulations, so code that reaches results/
# (an outside PR, a pasted fix) cannot read ~/.config API keys, ~/.ssh or push rights. Run: sudo scripts/setup_sandbox.sh
# Undo: sudo sysadminctl -deleteUser cmsim; sudo rm -rf /Users/Shared/cm-sim /etc/sudoers.d/cmsim; chmod 755 ~
set -eu
[ "$(id -u)" = 0 ] || { echo "run with sudo"; exit 1; }
OWNER=${SUDO_USER:?run via sudo from your own account}
HOMEDIR=$(dscl . -read /Users/$OWNER NFSHomeDirectory | awk '{print $2}')
BASE=/Users/Shared/cm-sim

# 1. nobody but the owner can enter the owner's home (it was 755: ~/.ssh and ~/.config were listable by other users)
chmod 700 "$HOMEDIR"
[ -f "$HOMEDIR/.config/colony/token.json" ] && chmod 600 "$HOMEDIR/.config/colony/token.json"

# 2. hidden standard (non-admin) user with a random password nobody knows
if ! id cmsim >/dev/null 2>&1; then
  sysadminctl -addUser cmsim -fullName "CM sim sandbox" -password "$(openssl rand -base64 24)" -home "$BASE/home" -shell /bin/zsh
  dscl . -create /Users/cmsim IsHidden 1
fi
mkdir -p "$BASE/home" "$BASE/work" "$BASE/in"
chown -R cmsim:staff "$BASE/home" "$BASE/work"; chmod 700 "$BASE/home"; chmod 755 "$BASE/work"
chown "$OWNER":staff "$BASE/in"; chmod 755 "$BASE/in"        # owner stages code here, cmsim reads it

# 3. the owner may run commands AS cmsim (a downgrade), never the reverse
echo "$OWNER ALL=(cmsim) NOPASSWD: ALL" > /etc/sudoers.d/cmsim
chmod 440 /etc/sudoers.d/cmsim
visudo -cf /etc/sudoers.d/cmsim

# 4. cmsim's own Python environment, pinned to the versions our recorded results used
cd /tmp   # cmsim cannot enter the owner's cwd; $BASE is root-owned, so the venv lives in cmsim's home
sudo -u cmsim -H /opt/homebrew/bin/python3.13 -m venv "$BASE/home/venv"
sudo -u cmsim -H "$BASE/home/venv/bin/pip" install -q pybamm==26.8.0.0 numpy==2.5.3
sudo -u cmsim -H "$BASE/home/venv/bin/python" -c "import pybamm; print('cmsim ready, pybamm', pybamm.__version__)"
# 5. prove the isolation
sudo -u cmsim cat "$HOMEDIR/.config/colony/credentials.json" >/dev/null 2>&1 && { echo "FAIL: cmsim can read owner secrets"; exit 1; } || echo "ok: cmsim cannot read $HOMEDIR"
