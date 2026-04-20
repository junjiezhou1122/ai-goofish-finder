from pydantic import ValidationError

from src.domain.models.direction import DirectionCreate, DirectionUpdate


def test_direction_create_normalizes_variants_and_strings():
    payload = DirectionCreate(
        name='  小红书起号  ',
        seed_topic=' 小红书运营 ',
        user_goal='  找商品词和服务词 ',
        preferred_variants=['product', 'service', 'product', 'delivery'],
        risk_level='HIGH',
    )

    assert payload.name == '小红书起号'
    assert payload.seed_topic == '小红书运营'
    assert payload.user_goal == '找商品词和服务词'
    assert payload.preferred_variants == ['product', 'service', 'delivery']
    assert payload.risk_level == 'high'
    assert payload.status == 'active'


def test_direction_update_rejects_empty_name():
    try:
        DirectionUpdate(name='   ')
    except ValidationError as exc:
        assert '字段不能为空' in str(exc)
    else:
        raise AssertionError('expected ValidationError')
