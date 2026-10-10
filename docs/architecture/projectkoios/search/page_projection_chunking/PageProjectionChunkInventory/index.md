# `PageProjectionChunkInventory`

`PageProjectionChunkInventory` owns the immutable canonical chunk order for one
exact page-projection result. It requires unique chunk identities and unique
increasing physical-page/block order. Its incremental length-framed SHA-256
identity binds the input result, contract version, and every ordered chunk ID,
including the valid empty inventory case.
