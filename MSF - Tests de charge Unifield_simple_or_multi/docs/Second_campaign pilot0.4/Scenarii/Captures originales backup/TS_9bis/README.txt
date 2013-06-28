1 register line à multiplier par 22.

uuid à changer
on peut réutiliser le même partner


23adf5823ecb11e2869ed4ae52a5e4b6/account_move_reconcile/1   <--- uuid et le 1 à changer




Pour vérifier que c'est bon:

register/accounting/bank register/
1 bank register si TS_10 fait en premier

En cliquant sur la ligne bank register, il devrait y en avoir 40 si 1 register. Sinon c'est 40x22

Dans generating rule:
	register line => 40x22
	account move (HQ) => 2x40x22 car 2 lignes par account move
	account move line (HQ) => 4x40x22
	analytical line => 40x22
