# Commit decided work through jetsam's plan/confirm flow.
# save() returns {'plan_id': ...}; confirm() takes id=. save ALONE DOES NOT
# COMMIT -- state that invariant in the intent or the model stops after save
# (measured 4/4).
save
confirm
log
