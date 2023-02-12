from pyteal import *

# This is the main ApprovalProgram of the contract.
def approval_program():

    scratch = ScratchVar(TealType.uint64)

    @Subroutine(TealType.uint64)
    def is_owner(addr):
      return addr == App.globalGet(Bytes("owner"))

    @Subroutine(TealType.uint64)
    def is_assessor(addr):
      return addr == App.globalGet(Bytes("green_assessor"))

    @Subroutine(TealType.uint64)
    def is_retailer(addr):
      return addr == App.globalGet(Bytes("retailer"))

    # Min balance 200000 microAlgos
    @Subroutine(TealType.none)
    def opt_in_asset():
      return Seq([
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.AssetTransfer,
            TxnField.asset_receiver: Global.current_application_address(),
            TxnField.asset_amount: Int(0),
            TxnField.xfer_asset: Txn.assets[0], # Must be in the assets array sent as part of the application call
        }),
        InnerTxnBuilder.Submit(),
      ])

    @Subroutine(TealType.none)
    def send_coins_to(addr: TealType.bytes, amount: TealType.uint64):
      return Seq([
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.AssetTransfer,
            TxnField.asset_receiver: addr,
            TxnField.asset_amount: amount,
            TxnField.xfer_asset: Txn.assets[0], # Must be in the assets array sent as part of the application call
        }),
        InnerTxnBuilder.Submit(),
      ])

    # Txn.application_args[0]: product id
    # Txn.application_args[1]: product name
    # Txn.application_args[2]: operation id
    # Txn.application_args[3]: operational data hash
    # Txn.application_args[4]: lca assessor address
    on_create = Seq([
      App.globalPut(Bytes("owner"), Txn.sender()),
      App.globalPut(Bytes("productId"), Txn.application_args[0]),
      App.globalPut(Bytes("productName"), Txn.application_args[1]),
      App.globalPut(Txn.application_args[2], Txn.application_args[3]),
      App.globalPut(Bytes("green_assessor"), Txn.application_args[4]),
      App.globalPut(Bytes("retailer"), Bytes("")),
      App.globalPut(Bytes("operationNo"), Int(1)),
      App.globalPut(Bytes("green"), Int(0)),
      App.globalPut(Bytes("at_retailer"), Int(0)),
      Approve(),
    ])

    # Txn.application_args[1]: operation id
    # Txn.application_args[2]: operational data hash
    append = Seq([
      scratch.store(App.globalGet(Bytes("operationNo"))),
      Assert(Global.group_size() == Int(1)),
      Assert(is_owner(Txn.sender()) == Int(1)),
      Assert(Txn.type_enum() == TxnType.ApplicationCall),
      Assert(Txn.application_args.length() == Int(3)),
      App.globalPut(Txn.application_args[1], Txn.application_args[2]),
      App.globalPut(Bytes("operationNo"), scratch.load() + Int(1)),
      If(is_retailer(Txn.sender())).Then(
        Seq([
          App.globalPut(Bytes("at_retailer"), Int(1)),
          opt_in_asset(),
        ])
      ),
      Approve(),
    ])

    no_green_available_at_retailer = And(
      App.globalGet(Bytes("at_retailer")) == Int(1), 
      App.globalGet(Bytes("green")) == Int(0)
    )

    # Transfer the SC ownership to the address specified at args[1]
    # Txn.application_args[1]: new owner addr
    transfer_ownership = Seq([
      Assert(Txn.type_enum() == TxnType.ApplicationCall),
      Assert(Global.group_size() == Int(1)),
      Assert(is_owner(Txn.sender()) == Int(1)),
      Assert(Txn.application_args.length() == Int(2)),
      App.globalPut(Bytes("owner"), Txn.application_args[1]),
      If(no_green_available_at_retailer).Then(
        Reject()
      ),
      Approve(),
    ])

    # Txn.application_args[1]: retailer addr
    set_retailer = Seq([
      Assert(Txn.type_enum() == TxnType.ApplicationCall),
      Assert(Global.group_size() == Int(1)),
      Assert(is_owner(Txn.sender()) == Int(1)),
      Assert(Txn.application_args.length() == Int(2)),
      Assert(Txn.application_args[1] != Txn.sender()),
      App.globalPut(Bytes("retailer"), Txn.application_args[1]),
      Approve(),
    ])

    fund_contract_check=And(
      Gtxn[2].type_enum() == TxnType.Payment,
      Gtxn[2].amount() >= Global.min_balance(),
      Gtxn[2].receiver() == Global.current_application_address(),
    )

    asset_transfer_check=And(
      Gtxn[1].type_enum() == TxnType.AssetTransfer,
      Gtxn[1].asset_amount() == Btoi(Gtxn[0].application_args[1]),
      Gtxn[1].asset_receiver() == Global.current_application_address(),
    )

    valid_set_lca = And(asset_transfer_check, fund_contract_check)

    # Gtxn[0]: set lca
    # Gtxn[1]: transfer coins to smart contract
    # Gtxn[2]: fund sc
    # Txn.application_args[1]: LCA points (green points)
    set_green = Seq([
      Assert(App.globalGet(Bytes("at_retailer")) == Int(1)),
      Assert(Global.group_size() == Int(3)),
      Assert(is_assessor(Gtxn[0].sender()) == Int(1)),
      Assert(Gtxn[0].type_enum() == TxnType.ApplicationCall),
      Assert(Gtxn[0].application_args.length() == Int(2)),
      Assert(valid_set_lca),
      App.globalPut(Bytes("green"), Btoi(Gtxn[0].application_args[1])),
      Approve(),
    ])

    claim = Seq([
      scratch.store(App.globalGet(Bytes("green"))),
      Assert(is_owner(Txn.sender()) == Int(1)),
      Assert(App.globalGet(Bytes("at_retailer")) == Int(1)),
      Assert(scratch.load() != Int(0)),
      send_coins_to(Txn.sender(), scratch.load()),
      Approve(),
    ])

    called_function = Txn.application_args[0]
    handle_noop = Cond(
      [called_function == Bytes("append"), append],
      [called_function == Bytes("transfer_ownership"), transfer_ownership],
      [called_function == Bytes("set_retailer"), set_retailer],
      [called_function == Bytes("set_green"), set_green],
      [called_function == Bytes("claim"), claim],
    )


    program = Cond(
        [Txn.application_id() == Int(0), on_create],
        [Txn.on_completion() == OnComplete.NoOp, handle_noop],
    )
    return program

def clear_state_program():
  program = Seq([
    Approve()
  ])
  return program

with open('greenvibes_approval.teal', 'w') as f:
    compiled = compileTeal(approval_program(), Mode.Application, version=5)
    f.write(compiled)

with open("greenvibes_clear.teal", "w") as f:
    compiled = compileTeal(clear_state_program(), mode=Mode.Application, version=5)
    f.write(compiled)