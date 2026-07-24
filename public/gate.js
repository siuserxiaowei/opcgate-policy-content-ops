export function evaluatePublicationGate(items = []) {
  const required = items.filter((item) => item.required !== false);
  const completed = required.filter((item) => item.checked === true);

  return {
    total: required.length,
    completed: completed.length,
    open: required.length > 0 && completed.length === required.length
  };
}
