# shellcheck shell=sh
# Installed as /etc/profile.d/thor.sh. Debian's /etc/profile resets PATH for
# every login shell (`bash -l`, `docker exec <c> bash -l`, ssh, the terminal
# tool's background `bash -lic`), dropping the image's ENV PATH dirs, so bare
# `thor` exits 127 there. Put them back in the ENV PATH order; dirs a login
# PATH already lists keep their position.
for __thor_p in /opt/data/.local/bin /opt/thor/.venv/bin /opt/thor/bin; do
    case ":$PATH:" in
        *":$__thor_p:"*) ;;
        *) PATH="$__thor_p:$PATH" ;;
    esac
done
unset __thor_p
export PATH
