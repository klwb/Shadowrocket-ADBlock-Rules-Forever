#!/usr/bin/env bash

set -euo pipefail

factory_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repository_root="$(dirname -- "${factory_dir}")"
backup_dir="$(mktemp -d)"
modified_files=()

restore_manual_files() {
  local target

  for target in "${modified_files[@]}"; do
    cp -p "${backup_dir}/${target}" "${factory_dir}/${target}"
  done

  rm -R -- "${backup_dir}"
}

trap restore_manual_files EXIT

apply_custom_file() {
  local custom_file="$1"
  local target_file="$2"

  if [[ ! -s "${factory_dir}/${custom_file}" ]]; then
    return
  fi

  cp -p "${factory_dir}/${target_file}" "${backup_dir}/${target_file}"
  modified_files+=("${target_file}")

  {
    printf "\n# ===== 自定义规则 (klwb) =====\n"
    cat "${factory_dir}/${custom_file}"
  } >> "${factory_dir}/${target_file}"
}

apply_custom_file custom_proxy.txt manual_proxy.txt
apply_custom_file custom_direct.txt manual_direct.txt
apply_custom_file custom_reject.txt manual_reject.txt
apply_custom_file custom_gfwlist.txt manual_gfwlist.txt
apply_custom_file custom_gfwlist_excludes.txt manual_gfwlist_excludes.txt

cd -- "${repository_root}"
"${factory_dir}/auto_build.sh"
