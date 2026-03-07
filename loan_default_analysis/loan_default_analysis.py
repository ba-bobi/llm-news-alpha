import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    RocCurveDisplay,
)
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier


def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="ISO-8859-1")
    return df


def build_preprocessor(df: pd.DataFrame, target_col: str):
    feature_cols = [c for c in df.columns if c != target_col]

    if "Id" in feature_cols:
        feature_cols.remove("Id")

    X = df[feature_cols]

    numeric_features = X.select_dtypes(include=[np.number]).columns.tolist()
    categorical_features = [c for c in X.columns if c not in numeric_features]

    numeric_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )

    categorical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, numeric_features),
            ("cat", categorical_transformer, categorical_features),
        ]
    )

    return X, preprocessor


def evaluate_model(name, model, X_train, X_test, y_train, y_test):
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    prob = model.predict_proba(X_test)[:, 1] if hasattr(model, "predict_proba") else None

    metrics = {
        "model": name,
        "accuracy": accuracy_score(y_test, pred),
        "precision": precision_score(y_test, pred, zero_division=0),
        "recall": recall_score(y_test, pred, zero_division=0),
        "f1": f1_score(y_test, pred, zero_division=0),
        "roc_auc": roc_auc_score(y_test, prob) if prob is not None else np.nan,
    }

    return model, metrics, pred, prob


def main(data_path: str):
    sns.set_theme(style="darkgrid")

    data_file = Path(data_path)
    if not data_file.exists():
        raise FileNotFoundError(f"Data file not found: {data_file}")

    out_dir = Path(__file__).resolve().parent / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)

    df = load_data(data_file)

    target_col = "Risk_Flag"
    if target_col not in df.columns:
        raise ValueError("`Risk_Flag` column is required in dataset")

    y = df[target_col].astype(int)
    X, preprocessor = build_preprocessor(df, target_col)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )

    models = {
        "LogisticRegression": LogisticRegression(max_iter=2000, class_weight="balanced"),
        "DecisionTree": DecisionTreeClassifier(max_depth=8, min_samples_leaf=20, random_state=42),
        "RandomForest": RandomForestClassifier(
            n_estimators=300,
            max_depth=10,
            min_samples_leaf=10,
            random_state=42,
            n_jobs=-1,
            class_weight="balanced_subsample",
        ),
    }

    results = []
    fitted_models = {}
    probs = {}

    for name, clf in models.items():
        pipe = Pipeline(steps=[("preprocess", preprocessor), ("model", clf)])
        fitted, m, pred, prob = evaluate_model(name, pipe, X_train, X_test, y_train, y_test)
        results.append(m)
        fitted_models[name] = fitted
        probs[name] = prob

    metrics_df = pd.DataFrame(results).sort_values("roc_auc", ascending=False)
    metrics_df.to_csv(out_dir / "metrics.csv", index=False)

    # Model comparison chart
    fig, ax = plt.subplots(figsize=(8, 4))
    plot_df = metrics_df.set_index("model")[["accuracy", "f1", "roc_auc"]]
    plot_df.plot(kind="bar", ax=ax)
    ax.set_title("Model Comparison")
    ax.set_ylim(0, 1)
    ax.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(out_dir / "model_comparison.png", dpi=150)
    plt.close()

    # Focus on RandomForest (usually strongest baseline)
    best_name = metrics_df.iloc[0]["model"]
    best_model = fitted_models[best_name]
    best_pred = best_model.predict(X_test)
    best_prob = probs[best_name]

    cm = confusion_matrix(y_test, best_pred)
    plt.figure(figsize=(4.5, 4))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues")
    plt.title(f"Confusion Matrix - {best_name}")
    plt.xlabel("Predicted")
    plt.ylabel("Actual")
    plt.tight_layout()
    plt.savefig(out_dir / "confusion_matrix_rf.png", dpi=150)
    plt.close()

    if best_prob is not None:
        RocCurveDisplay.from_predictions(y_test, best_prob)
        plt.title(f"ROC Curve - {best_name}")
        plt.tight_layout()
        plt.savefig(out_dir / "roc_curve_rf.png", dpi=150)
        plt.close()

    # Feature importance (if tree-based)
    if best_name in ["RandomForest", "DecisionTree"]:
        model_obj = best_model.named_steps["model"]
        pre = best_model.named_steps["preprocess"]
        feature_names = pre.get_feature_names_out()
        importances = model_obj.feature_importances_

        fi = (
            pd.DataFrame({"feature": feature_names, "importance": importances})
            .sort_values("importance", ascending=False)
            .head(20)
        )

        plt.figure(figsize=(8, 6))
        sns.barplot(data=fi, x="importance", y="feature")
        plt.title(f"Top 20 Feature Importance - {best_name}")
        plt.tight_layout()
        plt.savefig(out_dir / "feature_importance_rf.png", dpi=150)
        plt.close()

    print("=== Portfolio Summary ===")
    print(metrics_df.to_string(index=False))
    print(f"Outputs saved to: {out_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="Path to Training Data.csv")
    args = parser.parse_args()
    main(args.data)
