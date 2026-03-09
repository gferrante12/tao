/*================================================================
*   Filename   : convert.cpp
*   Author     : Yuyi Wang
*   Created on  Sat 9 Jan 2021 20:21:41 PM CST
*   Description:
*
================================================================*/

#include "convert.hpp"

using namespace H5;
using namespace std;

boost::container::pmr::monotonic_buffer_resource global_memory_resource{ 1024 * 1024 };

#define IMPL_H5TYPE(type, v) const DataType& h5_type<type>::value = PredType::v;

IMPL_H5TYPE(int8_t, NATIVE_INT8)
IMPL_H5TYPE(int16_t, NATIVE_INT16)
IMPL_H5TYPE(int32_t, NATIVE_INT32)
IMPL_H5TYPE(int64_t, NATIVE_INT64)
IMPL_H5TYPE(uint8_t, NATIVE_UINT8)
IMPL_H5TYPE(uint16_t, NATIVE_UINT16)
IMPL_H5TYPE(uint32_t, NATIVE_UINT32)
IMPL_H5TYPE(uint64_t, NATIVE_UINT64)
IMPL_H5TYPE(float, NATIVE_FLOAT)
IMPL_H5TYPE(double, NATIVE_DOUBLE)

static const DataType& get_str_type()
{
    static auto type = H5::PredType::C_S1;
    type.setSize(H5T_VARIABLE);
    return type;
}

const DataType& h5_type<const char*>::value = get_str_type();
