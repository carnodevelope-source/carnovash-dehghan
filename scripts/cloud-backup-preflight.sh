#!/bin/sh
# Read-only HOST check. Does not prepare permissions, mount disks or start services.
set -eu
mountpoint=/mnt/extra-storage
expected_uuid=${CLOUD_BACKUP_DISK_UUID:-e8c44715-a4e9-45cc-b1cc-932e8e5e2db2}
expected_device=${CLOUD_BACKUP_DEVICE:?Set reviewed Linux major:minor}
backup_uid=${CLOUD_BACKUP_UID:-10001}
backup_gid=${CLOUD_BACKUP_GID:-10001}
media_volume=${CLOUD_BACKUP_MEDIA_VOLUME:-carwash_carvash_media}
test "$(findmnt -rn -M "$mountpoint" -o UUID)" = "$expected_uuid"
test "$(findmnt -rn -M "$mountpoint" -o MAJ:MIN)" = "$expected_device"
test "$(findmnt -rn -M "$mountpoint" -o FSTYPE)" = ext4
case ",$(findmnt -rn -M "$mountpoint" -o OPTIONS)," in *,rw,*) ;; *) exit 1 ;; esac
destination=$mountpoint/cloud-backups
test -d "$destination"
test ! -L "$destination"
test "$(readlink -f "$destination")" = "$destination"
test "$(stat -c '%u:%g:%a' "$destination")" = "$backup_uid:$backup_gid:700"
test "$(stat -c '%d' "$destination")" = "$(stat -c '%d' "$mountpoint")"
test "$(docker info --format '{{.DockerRootDir}}')" = /mnt/server-data/docker
test "$(docker volume inspect --format '{{.Mountpoint}}' "$media_volume")" = "/mnt/server-data/docker/volumes/$media_volume/_data"
printf '%s\n' 'cloud_backup_host_preflight_ok'
