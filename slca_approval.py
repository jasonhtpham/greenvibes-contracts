from pyteal import *

# This is the main ApprovalProgram of the contract.
def approval_program():

    @Subroutine(TealType.none)
    def set_lca_to(app_idx, value):
      InnerTxnBuilder.Begin(),
      InnerTxnBuilder.SetFields({
          TxnField.type_enum: TxnType.ApplicationCall,
          TxnField.application_id: Int(app_idx),
          TxnField.application_args: [Bytes("set_lca"), Int(value)],
          TxnField.on_completion: OnComplete.NoOp,
      })
      InnerTxnBuilder.Submit()

    # Txn.application_args[0]: 
    # Txn.application_args[1]: 
    # Txn.application_args[2]: 
    # Txn.application_args[3]: 
    calculate_lca = Seq([
      
    ])

    called_function = Txn.application_args[0]
    handle_noop = Cond(
      [called_function == Bytes("calculate_lca"), calculate_lca],
    )


    program = Cond(
        # [Txn.application_id() == Int(0), on_create],
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