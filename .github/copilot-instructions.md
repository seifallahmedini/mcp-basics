### 🧱 Code Structure & Modularity
- **Never create a file longer than 500 lines of code.** If a file approaches this limit, refactor by splitting it into modules or helper files.
- **Organize code into clearly separated modules**, grouped by feature or responsibility.
- **Use clear, consistent imports** (prefer relative imports within packages).
- **Avoid circular imports** by ensuring that modules do not depend on each other in a circular manner.
- **Use `__init__.py` files** to mark directories as packages and to control what is imported when the package is imported.

### 📎 Style & Conventions
- **Use Python** as the primary language.
- **Follow PEP8**, use type hints, and format with `black`.
- **Use `pydantic` V2 for data validation**:
  - Use `@field_validator` instead of the deprecated `@validator`
  - Always include `@classmethod` decorator with field validators
  - Access validation context through the `info` parameter instead of `values`
  Example:
  ```python
  from pydantic import BaseModel, field_validator
  
  class Example(BaseModel):
      field: str
      
      @field_validator('field')
      @classmethod
      def validate_field(cls, v: str, info) -> str:
          return v
  ```
- Use `Flask` for APIs.
- Write **docstrings for every function** using the Google style:
  ```python
  def example():
      """
      Brief summary.

      Args:
          param1 (type): Description.

      Returns:
          type: Description.
      """
  ```

### 📚 Documentation & Explainability
- **Update `README.md`** when new features are added, dependencies change, or setup steps are modified.
- **Comment non-obvious code** and ensure everything is understandable to a mid-level developer.
- When writing complex logic, **add an inline `# Reason:` comment** explaining the why, not just the what.

### 🧠 AI Behavior Rules
- **Never assume missing context. Ask questions if uncertain.**
- **Never hallucinate libraries or functions** – only use known, verified Python packages.
- **Always confirm file paths and module names** exist before referencing them in code or tests.