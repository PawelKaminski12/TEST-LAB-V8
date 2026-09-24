# V10 FULL SYSTEM AUDIT

- Status: **FAIL**
- Checks: **201/208**
- App Script lines: **3038**
- SHA-256: `c02775feb441d093330ee91d2212a3564618e42ea8eb8eee3248cf537a14ec55`

## Failures
- FUNCTION_onOpen: count=2
- FUNCTION_V8_SETUP: count=2
- FUNCTION_ODSWIEZ_WSZYSTKO: count=2
- FUNCTION_alarmDirection_: count=2
- NO_DUPLICATE_FUNCTIONS: {'onOpen': 2, 'V8_SETUP': 2, 'ODSWIEZ_WSZYSTKO': 2, 'setupPortfolioLong_': 2, 'setupPortfolioTactical_': 2, 'setupSettings_': 2, 'setupExtremes_': 5, 'getExtremeSettings_': 2, 'buildExtremeAlarms_': 6, 'extremeLabel_': 2, 'writeExtremeAlarms_': 5, 'readActiveExtremeKeys_': 3, 'appendExtremeHistory_': 4, 'notifyNewExtremeAlarms_': 6, 'updateMainPanelExtremeSummary_': 6, 'panelEligibleExtreme_': 3, 'selectMainPanelExtreme_': 2, 'alarmDirection_': 2}
- NO_SUSPICIOUS_BARE_IDENTIFIERS: [(2227, 'range')]
- NO_WIDE_BREAKAPART: 

## Warnings
- None
