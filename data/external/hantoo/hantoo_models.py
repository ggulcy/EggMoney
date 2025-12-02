# -*- coding: utf-8 -*-
"""Hantoo API Data Models"""
from dataclasses import dataclass
from typing import List


@dataclass
class HantooExd:
    """Hantoo Exchange Information"""
    trading_exd: str  # Exchange code (NASD, AMEX, etc.)
    price_exd: str    # Price query exchange code (NAS, AMS, etc.)


@dataclass
class PriceOutput:
    """Price Query Response"""
    rsym: str
    zdiv: str
    base: str     # Previous close
    pvol: str
    last: str     # Current price
    sign: str
    diff: str
    rate: str
    tvol: str
    tamt: str
    ordy: str


@dataclass
class Balance1:
    """Balance Query Response - Output1 (Per Symbol)"""
    cano: str
    acnt_prdt_cd: str
    prdt_type_cd: str
    ovrs_pdno: str              # Overseas symbol
    ovrs_item_name: str         # Overseas item name
    frcr_evlu_pfls_amt: str     # Foreign currency evaluation profit/loss amount
    evlu_pfls_rt: str           # Evaluation profit/loss rate
    pchs_avg_pric: str          # Purchase average price
    ovrs_cblc_qty: str          # Overseas balance quantity
    ord_psbl_qty: str           # Order possible quantity
    frcr_pchs_amt1: str         # Foreign currency purchase amount
    ovrs_stck_evlu_amt: str     # Overseas stock evaluation amount
    now_pric2: str              # Current price
    tr_crcy_cd: str             # Trading currency code
    ovrs_excg_cd: str           # Overseas exchange code
    loan_type_cd: str
    loan_dt: str
    expd_dt: str


@dataclass
class Balance2:
    """Balance Query Response - Output2 (Account Summary)"""
    frcr_pchs_amt1: str          # Foreign currency purchase amount
    ovrs_rlzt_pfls_amt: str      # Overseas realized profit/loss amount
    ovrs_tot_pfls: str           # Overseas total profit/loss
    rlzt_erng_rt: str            # Realized earning rate
    tot_evlu_pfls_amt: str       # Total evaluation profit/loss amount
    tot_pftrt: str               # Total profit rate
    frcr_buy_amt_smtl1: str      # Foreign currency buy amount sum
    ovrs_rlzt_pfls_amt2: str     # Overseas realized profit/loss amount 2
    frcr_buy_amt_smtl2: str      # Foreign currency buy amount sum 2


@dataclass
class BalanceResult:
    """Balance Query Full Response"""
    ctx_area_fk200: str
    ctx_area_nk200: str
    output1: List[Balance1]
    output2: Balance2
    rt_cd: str
    msg_cd: str
    msg1: str


@dataclass
class OrderDetail:
    """Order Detail Information"""
    ord_dt: str                  # Order date
    ord_gno_brno: str
    odno: str                    # Order number
    orgn_odno: str
    sll_buy_dvsn_cd: str         # Sell/Buy division code
    sll_buy_dvsn_cd_name: str    # Sell/Buy division name
    rvse_cncl_dvsn: str
    rvse_cncl_dvsn_name: str
    pdno: str                    # Symbol
    prdt_name: str               # Product name
    ft_ord_qty: str              # Order quantity
    ft_ord_unpr3: str            # Order unit price
    ft_ccld_qty: str             # Filled quantity
    ft_ccld_unpr3: str           # Filled unit price
    ft_ccld_amt3: str            # Filled amount
    nccs_qty: str                # Unfilled quantity
    prcs_stat_name: str          # Process status name
    rjct_rson: str
    rjct_rson_name: str
    ord_tmd: str                 # Order time
    tr_mket_name: str
    tr_crcy_cd: str              # Trading currency code
    tr_natn: str
    ovrs_excg_cd: str
    tr_natn_name: str
    dmst_ord_dt: str
    thco_ord_tmd: str
    loan_type_cd: str
    loan_dt: str
    mdia_dvsn_name: str
    usa_amk_exts_rqst_yn: str
    splt_buy_attr_name: str


@dataclass
class AvailableAmount:
    """Available Amount Query Response"""
    tr_crcy_cd: str
    ord_psbl_frcr_amt: str
    sll_ruse_psbl_amt: str
    ovrs_ord_psbl_amt: str       # Overseas order possible amount
    max_ord_psbl_qty: str
    echm_af_ord_psbl_amt: str
    echm_af_ord_psbl_qty: str
    ord_psbl_qty: str
    exrt: str
    frcr_ord_psbl_amt1: str
    ovrs_max_ord_psbl_qty: str


@dataclass
class BalanceForTickerOutput1:
    """Ticker Balance Query - Output1 (Per Symbol Detail)"""
    pdno: str                    # Symbol
    prdt_name: str               # Product name
    cblc_qty13: str              # Balance quantity
    ord_psbl_qty1: str           # Order possible quantity
    avg_unpr3: str               # Average unit price
    ovrs_now_pric1: str          # Overseas current price
    frcr_pchs_amt: str           # Foreign currency purchase amount
    frcr_evlu_amt2: str          # Foreign currency evaluation amount
    evlu_pfls_amt2: str          # Evaluation profit/loss amount
    bass_exrt: str               # Base exchange rate
    oprt_dtl_dtime: str
    buy_crcy_cd: str             # Buy currency code
    thdt_sll_ccld_qty1: str      # Today sell filled quantity
    thdt_buy_ccld_qty1: str      # Today buy filled quantity
    evlu_pfls_rt1: str           # Evaluation profit/loss rate
    tr_mket_name: str            # Trading market name
    natn_kor_name: str           # Nation Korean name
    std_pdno: str
    mgge_qty: str
    loan_rmnd: str
    prdt_type_cd: str
    ovrs_excg_cd: str
    scts_dvsn_name: str
    ldng_cblc_qty: str


@dataclass
class BalanceForTickerOutput2:
    """Ticker Balance Query - Output2 (Per Currency Summary)"""
    crcy_cd: str                 # Currency code
    crcy_cd_name: str            # Currency name
    frcr_dncl_amt_2: str         # Foreign currency deposit amount
    frst_bltn_exrt: str          # First bulletin exchange rate
    frcr_evlu_amt2: str          # Foreign currency evaluation amount


@dataclass
class BalanceForTickerOutput3:
    """Ticker Balance Query - Output3 (Account Summary)"""
    pchs_amt_smtl_amt: str       # Purchase amount sum
    tot_evlu_pfls_amt: str       # Total evaluation profit/loss amount
    evlu_erng_rt1: str           # Evaluation earning rate
    tot_dncl_amt: str            # Total deposit amount
    wcrc_evlu_amt_smtl: str      # Won currency evaluation amount sum
    tot_asst_amt2: str           # Total asset amount
    frcr_cblc_wcrc_evlu_amt_smtl: str  # Foreign currency balance won currency evaluation amount sum
    tot_loan_amt: str            # Total loan amount
    tot_ldng_evlu_amt: str       # Total lending evaluation amount


@dataclass
class BalanceForTickers:
    """Ticker Balance Query Full Response"""
    output1: List[BalanceForTickerOutput1]
    output2: List[BalanceForTickerOutput2]
    output3: BalanceForTickerOutput3
    rt_cd: str
    msg_cd: str
    msg1: str


@dataclass
class TickerItem:
    """Ticker Item (Simplified holding info)"""
    ticker: str                  # Ticker symbol
    amount: float                # Quantity
    price: float                 # Current price
    total_price: float           # Total evaluation amount
