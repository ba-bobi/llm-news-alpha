# Loan Default Analysis (Portfolio Ready)

개인 대출 연체 예측 프로젝트를 포트폴리오 제출용으로 정리한 버전입니다.

## What was improved
- 하드코딩 경로 제거 (`--data` 인자 사용)
- 데이터 전처리 파이프라인화 (결측치/범주형 인코딩)
- 학습/검증 분리 및 클래스 불균형 대응(`stratify`)
- 3개 모델 비교(Logistic Regression / Decision Tree / Random Forest)
- 성능지표 출력 (Accuracy, Precision, Recall, F1, ROC-AUC)
- Confusion Matrix, ROC Curve, Feature Importance 시각화
- 결과물 자동 저장 (`outputs/`)

## Run
```bash
pip install -r requirements.txt
python loan_default_analysis.py --data "Training Data.csv"
```

## Output
- `outputs/metrics.csv`
- `outputs/model_comparison.png`
- `outputs/confusion_matrix_rf.png`
- `outputs/roc_curve_rf.png`
- `outputs/feature_importance_rf.png`

## Notes
- 타깃 변수는 `Risk_Flag`(1=연체, 0=정상) 기준입니다.
- 모델 해석은 리스크 분류 보조용이며, 실제 심사 정책은 별도 기준과 결합되어야 합니다.
