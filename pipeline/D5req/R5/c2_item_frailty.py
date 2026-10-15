# R5 C variant: piecewise-exponential model (items >= 1 y) with ITEM-level shared gamma frailty (instead of submitter),
# year dummies and quality covariates (evidence level, rating, type). Single-spell frailty is identified only by functional form.
import json, os
src = open('../R3_civic/r3_t4_survival.py', encoding='utf-8').read()
src = src.split("R = {'n_pieces'")[0] + "R = {}\n" + src[src.index("# (b) PEM"):src.index("json.dump(R, open('res_r3_t4.json'")]
src = src.replace("g = pd.factorize(P1.subU)[0]", "g = pd.factorize(P1.id)[0]")
os.chdir('../R3_civic'); exec(src); os.chdir('../R5')
out = R['b_pem_gamma_frailty_submitter_year_dummies']; out['note'] = 'frailty group = item (not submitter)'
json.dump({'pem_item_gamma_frailty': out}, open('res_c2_item_frailty.json', 'w'), indent=1); print(out)
