"""Quantities are stock units; document status and supply status stay separate."""
def coverage(required, issued, actual, reserved=0, drafts=0, own_drafts=0, incoming=0, requested=0):
    remaining=max(0,required-issued)
    other_holds=max(0,drafts-own_drafts)
    available=actual-reserved-other_holds
    shortage=max(0,remaining-available) if remaining>0 else 0
    to_buy=max(0,shortage-incoming)
    to_request=max(0,to_buy-requested)
    state='Đã cấp đủ' if remaining<=0 else 'Đủ hàng' if shortage<=0 else 'Chờ nhập' if to_buy<=0 else 'Đã đề nghị mua' if to_request<=0 else 'Cần mua'
    return dict(required_qty=required,issued_qty=issued,remaining_qty=remaining,actual_qty=actual,
        native_reserved_qty=reserved,draft_qty=drafts,own_draft_qty=own_drafts,other_hold_qty=other_holds,
        available_qty=available,shortage_qty=shortage,incoming_qty=incoming,requested_qty=requested,
        to_buy_qty=to_buy,to_request_qty=to_request,status=state)
