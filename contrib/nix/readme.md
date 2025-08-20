# YATB Components

1. YATB
2. Caddy - serving static
   1. should be on the same machine as yatb
3. FerretDB (as mongo replacement) - DB
   1. better be on the same machine as yatb
4. Dynamic tasks:
   1. k3s - master / slave
   2. Dynamic tasks controller (DTC)
      1. better be on k3s master
   3. etcd
      1. better be on all machines
   4. docker registry
      1. better be on k3s master
   5. minio
      1. can be anywhere
   6. s3 distributer
      1. better be on the same machine as minio, but can be on other...

So we have the next roles:

1. YATB
   1. Caddy
   2. FerretDB
   3. etcd if dynamic tasks
2. k3s master
   1. DTC
   2. etcd
   3. registry
3. storage
   1. minio
4. S3 svc

