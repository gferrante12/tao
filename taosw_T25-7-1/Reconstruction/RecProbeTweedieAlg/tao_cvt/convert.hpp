/*================================================================
*   Filename   : convert.hpp
*   Author     : Yuyi Wang
*   Created on  Fri 8 Jan 2021 19:44:11 PM CST
*   Description:
*
================================================================*/

#ifndef _CONVERTSIMDATA_H
#define _CONVERTSIMDATA_H

// To make clangd happy.
#include <limits>

#include "H5Cpp.h"
#include "H5PacketTable.h"
#include "TTree.h"
#include <algorithm>
#include <boost/container/pmr/monotonic_buffer_resource.hpp>
#include <boost/container/pmr/polymorphic_allocator.hpp>
#include <cstdint>
#include <ctime>
#include <string>
#include <tuple>
#include <vector>

extern boost::container::pmr::monotonic_buffer_resource global_memory_resource;

template <typename T>
struct h5_type;

#define SPEC_H5TYPE(type)                 \
    template <>                           \
    struct h5_type<type>                  \
    {                                     \
        static const H5::DataType& value; \
    };

SPEC_H5TYPE(std::int8_t)
SPEC_H5TYPE(std::int16_t)
SPEC_H5TYPE(std::int32_t)
SPEC_H5TYPE(std::int64_t)
SPEC_H5TYPE(std::uint8_t)
SPEC_H5TYPE(std::uint16_t)
SPEC_H5TYPE(std::uint32_t)
SPEC_H5TYPE(std::uint64_t)
SPEC_H5TYPE(const char*)
SPEC_H5TYPE(float)
SPEC_H5TYPE(double)

#define SPEC_H5TYPE_IMPL(type) \
    SPEC_H5TYPE(type)          \
    const H5::DataType& h5_type<type>::value = type::get_h5_type();

#define INSERT_TYPE(h5type, T, name, vtype) h5type.insertMember(#name, HOFFSET(T, name), vtype)
#define INSERT_(h5type, T, name) INSERT_TYPE(h5type, T, name, h5_type<decltype(T::name)>::value)

inline const char* get_raw_str(std::string const& str)
{
    boost::container::pmr::polymorphic_allocator<char> allocator{ &global_memory_resource };
    auto res = allocator.allocate(str.length() + 1);
    return std::char_traits<char>::copy(res, str.c_str(), str.length() + 1);
}

constexpr static std::size_t LOG_PROCESS_UNIT = 10000;

template <typename T>
struct buffered_packet_table
{
    constexpr static hsize_t buffer_size = 1000000000 / sizeof(T);

    FL_PacketTable m_table;
    std::vector<T> m_buffer;

public:
    buffered_packet_table(H5::Group const& group, const char* name, std::int64_t count, H5::DSetCreatPropList const& dsp)
        : m_table(FL_PacketTable(group.getId(), name, h5_type<T>::value.getId(), std::min<hsize_t>(count * sizeof(T), buffer_size), dsp.getId())),
          m_buffer()
    {
        m_buffer.reserve(buffer_size);
    }

    ~buffered_packet_table()
    {
        if (!m_buffer.empty())
        {
            flush_buffer();
        }
    }

    void push_back(T&& value)
    {
        m_buffer.push_back(std::move(value));
        if (m_buffer.size() >= buffer_size)
        {
            flush_buffer();
        }
    }

private:
    void flush_buffer()
    {
        m_table.AppendPackets(m_buffer.size(), m_buffer.data());
        m_buffer.clear();
    }
};

void transform_sim_header(TTree* sim_tree, H5::Group& output, const H5::DSetCreatPropList& dsp);
void transform_sim_event(TTree* sim_tree, H5::Group& output, const H5::DSetCreatPropList& dsp);

void transform_elec_event(TTree* elec_tree, H5::Group& output, const H5::DSetCreatPropList& dsp);

#endif
