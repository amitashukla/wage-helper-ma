interface Props {
  category: string;
}

export function ViolationCategoryBadge({ category }: Props) {
  return <span className="violation-badge">{category}</span>;
}
