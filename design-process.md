⌨️ Exercise 1.2: The Inputs
Perform these tasks in your code:

Task A: Create the Schema Open app/schemas.py. Create a new class PINCreate.

It must have one field: pin.

Use Pydantic's Field to enforce: min_length=4, max_length=4, and a regex pattern for digits only (pattern=r"^\d{4}$").

Task B: Locate your Hasher Open app/security.py (or wherever your login logic is).

Find the function that hashes passwords (usually get_password_hash or similar).

Ensure it is importable.

Task C: Create the Endpoint Shell Open app/routers/auth.py.

Import your new PINCreate schema.

Write a new endpoint POST /auth/set-pin.

For now, just make it accept the pin_data: PINCreate and return the raw pin back (echo) just to prove the validation works. Do not save to DB yet.

Submission: Paste the code for your PINCreate class and the POST /auth/set-pin endpoint.

<!-- ----------------------------- -->

Task B: Implement the Logic in app/routers/auth.py Update your set_pin function.

Dependency: Add user: User = Depends(get_current_user) and session: Session = Depends(get_session).

Guard Clause: Check if user.pin_hash is not None. If true, raise HTTPException(400, "PIN already set. Use change-pin endpoint.").

Hashing: Call your get_pin_hash(pin_data.pin).

Save: Update user.pin_hash, add to session, commit, and refresh.

Return: A simple success message: {"status": "success", "message": "Transaction PIN secured."}.