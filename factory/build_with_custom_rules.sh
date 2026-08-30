#!/usr/bin/env bash

set -euo pipefail

factory_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repository_root="$(dirname -- "${factory_dir}")"
backup_dir="$(mktemp -d)"
modified_files=("")

restore_manual_files() {
  local target

  for target in "${modified_files[@]}"; do
    [[ -z "${target}" ]] && continue
    mkdir -p -- "$(dirname -- "${factory_dir}/${target}")"
    cp -p "${backup_dir}/${target}" "${factory_dir}/${target}"
  done

  rm -R -- "${backup_dir}"
}

trap restore_manual_files EXIT

backup_target_file() {
  local target_file="$1"
  local existing_target

  for existing_target in "${modified_files[@]}"; do
    [[ -z "${existing_target}" ]] && continue
    if [[ "${existing_target}" == "${target_file}" ]]; then
      return
    fi
  done

  mkdir -p -- "$(dirname -- "${backup_dir}/${target_file}")"
  cp -p "${factory_dir}/${target_file}" "${backup_dir}/${target_file}"
  modified_files+=("${target_file}")
}

apply_custom_file() {
  local custom_file="$1"
  local target_file="$2"

  if [[ ! -s "${factory_dir}/${custom_file}" ]]; then
    return
  fi

  backup_target_file "${target_file}"

  {
    printf "\n# ===== 自定义规则 (klwb) =====\n"
    cat "${factory_dir}/${custom_file}"
  } >> "${factory_dir}/${target_file}"
}

apply_custom_skip_proxy() {
  local custom_file="custom_skip_proxy.txt"
  local target_file="template/sr_head.txt"
  local updated_file="${backup_dir}/sr_head.updated"

  if [[ ! -s "${factory_dir}/${custom_file}" ]]; then
    return
  fi

  backup_target_file "${target_file}"

  awk -v custom_file="${factory_dir}/${custom_file}" '
    function trim(value) {
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", value)
      return value
    }

    BEGIN {
      while ((getline custom_line < custom_file) > 0) {
        custom_line = trim(custom_line)
        if (custom_line == "" || custom_line ~ /^#/) {
          continue
        }
        custom_items[++custom_count] = custom_line
      }
      close(custom_file)
    }

    /^\[General\][[:space:]]*$/ {
      in_general = 1
    }

    /^\[/ && !/^\[General\][[:space:]]*$/ {
      in_general = 0
    }

    in_general && !updated && /^[[:space:]]*skip-proxy[[:space:]]*=/ {
      separator = index($0, "=")
      prefix = substr($0, 1, separator)
      value = substr($0, separator + 1)
      output = ""

      existing_count = split(value, existing_items, ",")
      for (index_item = 1; index_item <= existing_count; index_item++) {
        item = trim(existing_items[index_item])
        if (item != "" && !seen[item]++) {
          output = output (output == "" ? "" : ", ") item
        }
      }

      for (index_item = 1; index_item <= custom_count; index_item++) {
        item = custom_items[index_item]
        if (!seen[item]++) {
          output = output (output == "" ? "" : ", ") item
        }
      }

      print prefix " " output
      updated = 1
      next
    }

    { print }

    END {
      if (!updated) {
        print "Could not find [General] skip-proxy in " FILENAME > "/dev/stderr"
        exit 42
      }
    }
  ' "${factory_dir}/${target_file}" > "${updated_file}"

  cp "${updated_file}" "${factory_dir}/${target_file}"
}

apply_custom_file custom_proxy.txt manual_proxy.txt
apply_custom_file custom_direct.txt manual_direct.txt
apply_custom_file custom_reject.txt manual_reject.txt
apply_custom_file custom_gfwlist.txt manual_gfwlist.txt
apply_custom_file custom_gfwlist_excludes.txt manual_gfwlist_excludes.txt
apply_custom_skip_proxy

cd -- "${repository_root}"
"${factory_dir}/auto_build.sh"
