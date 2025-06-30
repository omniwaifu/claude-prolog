% Bank Loan Approval System - Pure Rules Only
% ============================================
% No data embedded - rules only for decision logic

% Credit Score Categories
excellent_credit(Name) :- applicant(Name, _, _, Score, _, _, _, _), Score >= 750.
good_credit(Name) :- applicant(Name, _, _, Score, _, _, _, _), Score >= 650, Score < 750.
fair_credit(Name) :- applicant(Name, _, _, Score, _, _, _, _), Score >= 550, Score < 650.
poor_credit(Name) :- applicant(Name, _, _, Score, _, _, _, _), Score < 550.

% Income Categories (annual)
high_income(Name) :- applicant(Name, _, Income, _, _, _, _, _), Income >= 100000.
medium_income(Name) :- applicant(Name, _, Income, _, _, _, _, _), Income >= 50000, Income < 100000.
low_income(Name) :- applicant(Name, _, Income, _, _, _, _, _), Income < 50000.

% Employment Stability
stable_employment(Name) :- 
    employment_status(Name, permanent),
    applicant(Name, _, _, _, Years, _, _, _),
    Years >= 2.

unstable_employment(Name) :- 
    employment_status(Name, contract);
    (applicant(Name, _, _, _, Years, _, _, _), Years < 2).

% Debt-to-Income Ratio Assessment
low_debt_ratio(Name) :- applicant(Name, _, _, _, _, Ratio, _, _), Ratio =< 0.30.
moderate_debt_ratio(Name) :- applicant(Name, _, _, _, _, Ratio, _, _), Ratio > 0.30, Ratio =< 0.45.
high_debt_ratio(Name) :- applicant(Name, _, _, _, _, Ratio, _, _), Ratio > 0.45.

% Loan-to-Income Ratio
reasonable_loan_amount(Name) :-
    applicant(Name, _, Income, _, _, _, LoanAmount, _),
    Ratio is LoanAmount / Income,
    Ratio =< 5.0.

excessive_loan_amount(Name) :-
    applicant(Name, _, Income, _, _, _, LoanAmount, _),
    Ratio is LoanAmount / Income,
    Ratio > 5.0.

% Asset Assessment
sufficient_assets(Name) :-
    assets(Name, Property, Savings, Investments),
    applicant(Name, _, _, _, _, _, LoanAmount, _),
    TotalAssets is Property + Savings + Investments,
    TotalAssets >= LoanAmount * 0.2. % 20% of loan amount in assets

% Credit History Assessment
clean_credit_history(Name) :-
    credit_history(Name, Late, Bankruptcies, Defaults),
    Late =< 2,
    Bankruptcies = 0,
    Defaults = 0.

problematic_credit_history(Name) :-
    credit_history(Name, Late, Bankruptcies, Defaults),
    (Late > 5; Bankruptcies > 0; Defaults > 2).

% Age-based rules
mature_applicant(Name) :- applicant(Name, Age, _, _, _, _, _, _), Age >= 25, Age =< 65.
young_applicant(Name) :- applicant(Name, Age, _, _, _, _, _, _), Age < 25.
senior_applicant(Name) :- applicant(Name, Age, _, _, _, _, _, _), Age > 65.

% Loan Purpose Risk Assessment
low_risk_purpose(Name) :- applicant(Name, _, _, _, _, _, _, mortgage).
low_risk_purpose(Name) :- applicant(Name, _, _, _, _, _, _, car).
medium_risk_purpose(Name) :- applicant(Name, _, _, _, _, _, _, education).
high_risk_purpose(Name) :- applicant(Name, _, _, _, _, _, _, personal).
high_risk_purpose(Name) :- applicant(Name, _, _, _, _, _, _, business).

% PRIMARY APPROVAL RULES
% ======================

% Automatic Approval - Premium Customers
auto_approve(Name) :-
    excellent_credit(Name),
    stable_employment(Name),
    low_debt_ratio(Name),
    sufficient_assets(Name),
    clean_credit_history(Name),
    reasonable_loan_amount(Name),
    mature_applicant(Name).

% Standard Approval - Good Candidates
standard_approve(Name) :-
    good_credit(Name),
    stable_employment(Name),
    moderate_debt_ratio(Name),
    clean_credit_history(Name),
    reasonable_loan_amount(Name),
    mature_applicant(Name),
    low_risk_purpose(Name).

% Conditional Approval - Requires Additional Review
conditional_approve(Name) :-
    fair_credit(Name),
    stable_employment(Name),
    moderate_debt_ratio(Name),
    reasonable_loan_amount(Name),
    mature_applicant(Name),
    \+ problematic_credit_history(Name).

% Manual Review Required
manual_review(Name) :-
    good_credit(Name),
    (unstable_employment(Name); high_debt_ratio(Name)),
    reasonable_loan_amount(Name),
    \+ problematic_credit_history(Name).

manual_review(Name) :-
    fair_credit(Name),
    stable_employment(Name),
    high_risk_purpose(Name),
    sufficient_assets(Name).

% Automatic Rejection
auto_reject(Name) :-
    poor_credit(Name).

auto_reject(Name) :-
    problematic_credit_history(Name),
    (high_debt_ratio(Name); excessive_loan_amount(Name)).

auto_reject(Name) :-
    excessive_loan_amount(Name),
    (unstable_employment(Name); high_debt_ratio(Name)).

% Final Decision Logic
approved(Name) :- auto_approve(Name).
approved(Name) :- standard_approve(Name).

conditionally_approved(Name) :- conditional_approve(Name), \+ approved(Name).

needs_review(Name) :- manual_review(Name), \+ approved(Name), \+ conditionally_approved(Name).

rejected(Name) :- auto_reject(Name).
rejected(Name) :- \+ approved(Name), \+ conditionally_approved(Name), \+ needs_review(Name).

% Risk Assessment
low_risk(Name) :- auto_approve(Name).
medium_risk(Name) :- standard_approve(Name); conditional_approve(Name).
high_risk(Name) :- manual_review(Name); auto_reject(Name).

% Interest Rate Determination (basis points above base rate)
interest_rate_premium(Name, 0) :- auto_approve(Name).
interest_rate_premium(Name, 50) :- standard_approve(Name).
interest_rate_premium(Name, 150) :- conditional_approve(Name).
interest_rate_premium(Name, 300) :- manual_review(Name).
interest_rate_premium(Name, 9999) :- auto_reject(Name). % Rejection marker 